package com.vitekkor.perffect.compiler

import com.vitekkor.perffect.compiler.model.CompilationResult
import com.vitekkor.perffect.compiler.model.InvokeStatus
import com.vitekkor.perffect.compiler.model.KotlincInvokeStatus
import com.vitekkor.perffect.compiler.util.MessageCollectorImpl
import com.vitekkor.perffect.config.CompilerArgs
import com.vitekkor.perffect.project.Project
import com.vitekkor.perffect.util.WithLogger
import org.apache.commons.io.FileUtils
import org.jetbrains.kotlin.cli.common.arguments.K2JVMCompilerArguments
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation
import org.jetbrains.kotlin.cli.jvm.K2JVMCompiler
import org.jetbrains.kotlin.config.Services
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

open class KotlinJVMCompiler(
    override val arguments: String = ""
) : BaseCompiler(), WithLogger {
    override val compilerInfo: String
        get() = "Kotlin JVM $arguments"

    override var pathToCompiled: String = CompilerArgs.pathToTmpDir + "/kotlin"

    override fun checkCompiling(project: Project): Boolean {
        val status = tryToCompile(project)
        return !MessageCollectorImpl.hasCompileError && !status.hasTimeout && !MessageCollectorImpl.hasException
    }

    override fun getErrorMessageWithLocation(project: Project): Pair<String, List<CompilerMessageSourceLocation>> {
        val status = tryToCompile(project)
        return status.combinedOutput to status.locations
    }

    override fun compile(project: Project, includeRuntime: Boolean): CompilationResult {
        return getCompilationResult(project, includeRuntime)
    }

    private fun getCompilationResult(projectWithMainFun: Project, includeRuntime: Boolean): CompilationResult {
        val path = projectWithMainFun.saveOrRemoveToTmp(true)
        val args = prepareArgs(path, pathToCompiled)
        val status = executeCompiler(projectWithMainFun, args)
        if (status.hasException || status.hasTimeout || !status.isCompileSuccess) return CompilationResult(-1, "")
        return CompilationResult(0, pathToCompiled)
    }

    private fun prepareArgs(path: String, destination: String): K2JVMCompilerArguments {
        val destFile = File(destination)
        if (destFile.isFile) {
            destFile.delete()
        } else if (destFile.isDirectory) FileUtils.cleanDirectory(destFile)
        val projectArgs = K2JVMCompilerArguments().apply {
            K2JVMCompiler().parseArguments(
                arrayOf(),
                this
            )
        }
        val compilerArgs =
            if (arguments.isEmpty()) {
                "$path -d $destination".split(" ")
            } else {
                "$path $arguments -d $destination".split(" ")
            }
        projectArgs.apply { K2JVMCompiler().parseArguments(compilerArgs.toTypedArray(), this) }
        projectArgs.classpath =
            "${CompilerArgs.jvmStdLibPaths.joinToString(separator = ":")}:${System.getProperty("java.class.path")}"
                .split(":")
                .filter { it.isNotEmpty() }
                .toSet().toList()
                .joinToString(":")
        projectArgs.jvmTarget = "1.8"
        projectArgs.optIn = arrayOf("kotlin.ExperimentalStdlibApi", "kotlin.contracts.ExperimentalContracts")
        return projectArgs
    }

    override fun executeCompiler(project: Project, args: Any): InvokeStatus {
        args as K2JVMCompilerArguments
        val compiler = K2JVMCompiler()
        val services = Services.EMPTY
        MessageCollectorImpl.clear()
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
        val args = prepareArgs(path, pathToCompiled)
        return executeCompiler(project, args) as KotlincInvokeStatus
    }
}
