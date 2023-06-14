package com.vitekkor.compiler

import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.util.io.FileUtilRt
import com.vitekkor.compiler.model.CompilationResult
import com.vitekkor.compiler.model.CompileStatus
import com.vitekkor.compiler.model.InvokeStatus
import com.vitekkor.compiler.model.Stream
import com.vitekkor.config.CompilerArgs
import com.vitekkor.project.Project
import org.apache.commons.exec.CommandLine
import org.apache.commons.exec.DefaultExecutor
import org.apache.commons.exec.ExecuteException
import org.apache.commons.exec.ExecuteWatchdog
import org.apache.commons.exec.PumpStreamHandler
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation
import org.jetbrains.kotlin.cli.jvm.compiler.CompileEnvironmentException
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileInputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.jar.JarInputStream
import java.util.jar.JarOutputStream

abstract class BaseCompiler {

    abstract val arguments: String
    abstract fun checkCompiling(project: Project): Boolean
    abstract fun getErrorMessageWithLocation(project: Project): Pair<String, List<CompilerMessageSourceLocation>>
    abstract fun tryToCompile(project: Project): InvokeStatus
    abstract fun compile(project: Project, includeRuntime: Boolean = true): CompilationResult

    protected abstract fun executeCompiler(project: Project, args: Any): InvokeStatus

    abstract val compilerInfo: String
    abstract var pathToCompiled: String

    protected val threadPool: ExecutorService = Executors.newCachedThreadPool()

    fun tryToCompileWithStatus(project: Project): CompileStatus {
        val status = tryToCompile(project)
        return when {
            status.hasException -> CompileStatus.BUG
            status.hasCompilationError() || status.hasTimeout -> CompileStatus.ERROR
            status.isCompileSuccess -> CompileStatus.OK
            else -> CompileStatus.ERROR
        }
    }

    fun tryToCompileWithStatusAndExecutionTime(project: Project): Pair<CompileStatus, Long> {
        val invokeStatus = tryToCompile(project)
        val compilationStatus =
            when {
                invokeStatus.hasException -> CompileStatus.BUG
                invokeStatus.hasCompilationError() || invokeStatus.hasTimeout -> CompileStatus.ERROR
                invokeStatus.isCompileSuccess -> CompileStatus.OK
                else -> CompileStatus.ERROR
            }
        return compilationStatus to invokeStatus.compilerExecTimeMillis
    }

    fun commonExec(command: String, streamType: Stream = Stream.INPUT, timeoutSec: Long = 5L): String {
        val cmdLine = CommandLine.parse(command)
        val outputStream = ByteArrayOutputStream()
        val errorStream = ByteArrayOutputStream()
        val executor = DefaultExecutor().also {
            it.watchdog = ExecuteWatchdog(timeoutSec * 1000)
            it.streamHandler = PumpStreamHandler(outputStream, errorStream)
        }
        try {
            executor.execute(cmdLine)
        } catch (e: ExecuteException) {
            executor.watchdog.destroyProcess()
            var streamOutput = when (streamType) {
                Stream.INPUT -> outputStream.toString()
                Stream.ERROR -> errorStream.toString()
                else -> "" + errorStream.toString()
            }
            if (errorStream.toString().isEmpty() || errorStream.toString().contains("StackOverflow", true)) {
                streamOutput = "Exception timeout"
            }
            return streamOutput
        }
        return when (streamType) {
            Stream.INPUT -> outputStream.toString()
            Stream.ERROR -> errorStream.toString()
            Stream.BOTH -> "OUTPUTSTREAM:\n$outputStream ERRORSTREAM:\n$errorStream"
        }
    }

    fun getExecutionTime(path: String, streamType: Stream = Stream.BOTH, mainClass: String = ""): Pair<String, Long> {
        val startTime = System.currentTimeMillis()
        val execRes = exec(path, streamType, mainClass)
        return execRes to System.currentTimeMillis() - startTime
    }

    fun copyFullJarImpl(stream: JarOutputStream, jarPath: File) {
        JarInputStream(FileInputStream(jarPath)).use { jis ->
            while (true) {
                val e = jis.nextJarEntry ?: break
                stream.putNextEntry(e)
                FileUtil.copy(jis, stream)
            }
        }
    }

    fun writeRuntimeToJar(lib: String, stream: JarOutputStream) {
        val stdlibPath = File(lib)
        if (!stdlibPath.exists()) {
            throw CompileEnvironmentException("Couldn't find kotlin-stdlib at $stdlibPath")
        }
        copyJarImpl(stream, stdlibPath)
    }

    fun copyJarImpl(stream: JarOutputStream, jarPath: File) {
        JarInputStream(FileInputStream(jarPath)).use { jis ->
            while (true) {
                val e = jis.nextJarEntry ?: break
                if (FileUtilRt.extensionEquals(e.name, "class")) {
                    try {
                        stream.putNextEntry(e)
                        FileUtil.copy(jis, stream)
                    } catch (e: Exception) {
                        continue
                    }
                }
            }
        }
    }

    fun exec(path: String, streamType: Stream = Stream.INPUT, mainClass: String = ""): String {
        val cp = if (this is JavaCompiler) {
            path
        } else {
            "${CompilerArgs.jvmStdLibPaths.joinToString(":")}:$path"
        }
        return commonExec("java -classpath $cp $mainClass", streamType)
    }

    fun cleanUp() {
        File(pathToCompiled).deleteRecursively()
    }

    override fun toString(): String = compilerInfo
}
