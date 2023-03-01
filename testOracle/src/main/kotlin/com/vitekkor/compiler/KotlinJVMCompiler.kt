package com.vitekkor.compiler

import com.vitekkor.compiler.model.CompilationResult
import com.vitekkor.compiler.model.KotlincInvokeStatus
import com.vitekkor.compiler.model.Stream
import com.vitekkor.compiler.util.MessageCollectorImpl
import com.vitekkor.config.CompilerArgs
import com.vitekkor.project.Directives
import com.vitekkor.project.Project
import com.vitekkor.util.WithLogger
import org.apache.commons.io.FileUtils
import org.jetbrains.kotlin.cli.common.arguments.K2JVMCompilerArguments
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation
import org.jetbrains.kotlin.cli.jvm.K2JVMCompiler
import org.jetbrains.kotlin.config.Services
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import java.util.jar.JarInputStream
import java.util.jar.JarOutputStream

open class KotlinJVMCompiler(
    override val arguments: String = ""
) : BaseCompiler(), WithLogger {
    override val compilerInfo: String
        get() = "JVM $arguments"

    override var pathToCompiled: String = CompilerArgs.pathToTmpDir + "/tmp.jar"


    override fun checkCompiling(project: Project): Boolean {
        val status = tryToCompile(project)
        return !MessageCollectorImpl.hasCompileError && !status.hasTimeout && !MessageCollectorImpl.hasException
    }

    override fun getErrorMessageWithLocation(project: Project): Pair<String, List<CompilerMessageSourceLocation>> {
        val status = tryToCompile(project)
        return status.combinedOutput to status.locations
    }

    override fun isCompilerBug(project: Project): Boolean =
        tryToCompile(project).hasException

    override fun compile(project: Project, includeRuntime: Boolean): CompilationResult {
        return getCompilationResult(project, includeRuntime)
    }

    private fun getCompilationResult(projectWithMainFun: Project, includeRuntime: Boolean): CompilationResult {
        val path = projectWithMainFun.saveOrRemoveToTmp(true)
        val tmpJar = "$pathToCompiled.jar"
        val args = prepareArgs(projectWithMainFun, path, tmpJar)
        val status = executeCompiler(projectWithMainFun, args)
        if (status.hasException || status.hasTimeout || !status.isCompileSuccess) return CompilationResult(-1, "")
        val res = File(pathToCompiled)
        val input = JarInputStream(File(tmpJar).inputStream())
        val output = JarOutputStream(res.outputStream(), input.manifest)
        copyFullJarImpl(output, File(tmpJar))
        if (includeRuntime)
            CompilerArgs.jvmStdLibPaths.forEach { writeRuntimeToJar(it, output) }
        output.finish()
        input.close()
        File(tmpJar).delete()
        return CompilationResult(0, pathToCompiled)
    }

    private fun prepareArgs(project: Project, path: String, destination: String): K2JVMCompilerArguments {
        val destFile = File(destination)
        if (destFile.isFile) destFile.delete()
        else if (destFile.isDirectory) FileUtils.cleanDirectory(destFile)
        val projectArgs = project.getProjectSettingsAsCompilerArgs("JVM") as K2JVMCompilerArguments
        val compilerArgs =
            if (arguments.isEmpty())
                "$path -d $destination".split(" ")
            else
                "$path $arguments -d $destination".split(" ")
        projectArgs.apply { K2JVMCompiler().parseArguments(compilerArgs.toTypedArray(), this) }
        projectArgs.classpath =
            "${CompilerArgs.jvmStdLibPaths.joinToString(separator = ":")}:${System.getProperty("java.class.path")}"
                .split(":")
                .filter { it.isNotEmpty() }
                .toSet().toList()
                .joinToString(":")
        projectArgs.jvmTarget = "1.8"
        projectArgs.optIn = arrayOf("kotlin.ExperimentalStdlibApi", "kotlin.contracts.ExperimentalContracts")
        if (project.configuration.jvmDefault.isNotEmpty())
            projectArgs.jvmDefault = project.configuration.jvmDefault.substringAfter(Directives.jvmDefault)
        return projectArgs
    }

    private fun executeCompiler(project: Project, args: K2JVMCompilerArguments): KotlincInvokeStatus {
        val compiler = K2JVMCompiler()
        val services = Services.EMPTY
        MessageCollectorImpl.clear()
        val threadPool = Executors.newCachedThreadPool()
        val futureExitCode = threadPool.submit {
            compiler.exec(MessageCollectorImpl, services, args)
        }
        var hasTimeout = false
        var compilerWorkingTime: Long = -1
        try {
            val startTime = System.currentTimeMillis()
            futureExitCode.get(10L, TimeUnit.SECONDS)
            compilerWorkingTime = System.currentTimeMillis() - startTime
        } catch (ex: TimeoutException) {
            hasTimeout = true
            futureExitCode.cancel(true)
        } finally {
            project.saveOrRemoveToTmp(false)
        }
        return KotlincInvokeStatus(
            MessageCollectorImpl.crashMessages.joinToString("\n") +
                MessageCollectorImpl.compileErrorMessages.joinToString("\n"),
            !MessageCollectorImpl.hasCompileError,
            MessageCollectorImpl.hasException,
            hasTimeout,
            compilerWorkingTime,
            MessageCollectorImpl.locations.toMutableList()
        )
    }

    override fun tryToCompile(project: Project): KotlincInvokeStatus {
        val path = project.saveOrRemoveToTmp(true)
        val trashDir = "${CompilerArgs.pathToTmpDir}/trash/"
        val args = prepareArgs(project, path, trashDir)
        return executeCompiler(project, args)
    }

    override fun exec(path: String, streamType: Stream, mainClass: String): String {
        val mc =
            mainClass.ifEmpty { JarInputStream(File(path).inputStream()).manifest.mainAttributes.getValue("Main-class") }
        return commonExec(
            "java -classpath ${CompilerArgs.jvmStdLibPaths.joinToString(":")}:$path $mc",
            streamType
        )
    }
}
