package com.vitekkor.perffect.compiler

import com.vitekkor.perffect.compiler.model.CompilationResult
import com.vitekkor.perffect.compiler.model.CompileStatus
import com.vitekkor.perffect.compiler.model.InvokeStatus
import com.vitekkor.perffect.compiler.model.Stream
import com.vitekkor.perffect.config.CompilerArgs
import com.vitekkor.perffect.project.Project
import org.apache.commons.exec.CommandLine
import org.apache.commons.exec.DefaultExecutor
import org.apache.commons.exec.ExecuteException
import org.apache.commons.exec.ExecuteWatchdog
import org.apache.commons.exec.PumpStreamHandler
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * An abstract class that provides the basic structure and methods to compile a project for different compilers.
 */
abstract class BaseCompiler {

    /**
     * The command line arguments for the compiler.
     */
    abstract val arguments: String

    /**
     * Checks whether the project can be compiled by the compiler.
     * @param project the project to check
     * @return true if the project can be compiled, false otherwise
     */
    abstract fun checkCompiling(project: Project): Boolean

    /**
     * Returns the error message with location from the compiler.
     * @param project the project to compile
     * @return a pair of the error message and its source locations
     */
    abstract fun getErrorMessageWithLocation(project: Project): Pair<String, List<CompilerMessageSourceLocation>>

    /**
     * Attempts to compile the project using the compiler.
     * @param project the project to compile
     * @return the status of the compilation attempt
     */
    abstract fun tryToCompile(project: Project): InvokeStatus

    /**
     * Compiles the project using the compiler.
     * @param project the project to compile
     * @param includeRuntime whether to include the runtime in the compilation
     * @return the result of the compilation
     */
    abstract fun compile(project: Project, includeRuntime: Boolean = true): CompilationResult

    /**
     * Executes the compiler with the given arguments.
     * @param project the project to compile
     * @param args the arguments to pass to the compiler
     * @return the status of the compilation attempt
     */
    protected abstract fun executeCompiler(project: Project, args: Any): InvokeStatus

    /**
     * Information about the compiler.
     */
    abstract val compilerInfo: String

    /**
     * The path to the compiled project.
     */
    abstract var pathToCompiled: String

    /**
     * Thread pool for executing tasks asynchronously.
     */
    protected val threadPool: ExecutorService = Executors.newCachedThreadPool()

    /**
     * Attempts to compile the project and returns the compilation status and execution time.
     * @param project the project to compile
     * @return a pair of the compilation status and the execution time in milliseconds
     */
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

    /**
     * Executes a command in the terminal with the given timeout and returns the output stream.
     * @param command the command to execute
     * @param streamType the type of output stream to return (INPUT, ERROR, or BOTH)
     * @param timeoutSec the number of seconds to wait before timing out
     * @return the output stream as a string
     */
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

    /**
     * Returns the execution time of a compiled project.
     * @param path the path to the compiled project
     * @param streamType the type of output stream to return (INPUT, ERROR, or BOTH)
     * @param mainClass the main class of the project
     * @return a pair of the output stream and the execution time in milliseconds
     */
    fun getExecutionTime(path: String, streamType: Stream = Stream.BOTH, mainClass: String = ""): Pair<String, Long> {
        val startTime = System.currentTimeMillis()
        val execRes = exec(path, streamType, mainClass)
        return execRes to System.currentTimeMillis() - startTime
    }

    /**
     * Executes a compiled project.
     * @param path the path to the compiled project
     * @param streamType the type of output stream to return (INPUT, ERROR, or BOTH)
     * @param mainClass the main class of the project
     * @return the output stream as a string
     */
    fun exec(path: String, streamType: Stream = Stream.INPUT, mainClass: String = ""): String {
        val cp = if (this is JavaCompiler) {
            path
        } else {
            "${CompilerArgs.jvmStdLibPaths.joinToString(":")}:$path"
        }
        return commonExec("java -classpath $cp $mainClass", streamType)
    }

    /**
     * Deletes the compiled project.
     */
    fun cleanUp() {
        File(pathToCompiled).deleteRecursively()
    }

    override fun toString(): String = compilerInfo
}
