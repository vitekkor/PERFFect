package com.vitekkor.perffect.compiler

import com.vitekkor.perffect.compiler.model.CompilationResult
import com.vitekkor.perffect.compiler.model.InvokeStatus
import com.vitekkor.perffect.compiler.model.JavacInvokeStatus
import com.vitekkor.perffect.config.CompilerArgs
import com.vitekkor.perffect.project.Project
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageLocation
import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation
import java.io.File
import java.util.Locale
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import javax.tools.Diagnostic
import javax.tools.DiagnosticCollector
import javax.tools.JavaFileObject
import javax.tools.ToolProvider

/**
 * A compiler that compiles Java code.
 * @param arguments the command line arguments for the compiler
 */
class JavaCompiler(override val arguments: String = "") : BaseCompiler() {
    override val compilerInfo: String
        get() = "Java $arguments"

    override var pathToCompiled: String = CompilerArgs.pathToTmpDir + "/java"

    override fun checkCompiling(project: Project): Boolean {
        val status = tryToCompile(project)
        return status.isCompileSuccess && !status.hasTimeout && !status.hasException
    }

    override fun getErrorMessageWithLocation(project: Project): Pair<String, List<CompilerMessageSourceLocation>> {
        val status = tryToCompile(project)
        return status.combinedOutput to status.locations
    }

    override fun tryToCompile(project: Project): InvokeStatus {
        return executeCompilerInternal(project)
    }

    override fun compile(project: Project, includeRuntime: Boolean): CompilationResult {
        val compilerInvokeStatus = executeCompilerInternal(project)
        if (compilerInvokeStatus.hasException || compilerInvokeStatus.hasTimeout || !compilerInvokeStatus.isCompileSuccess) {
            return CompilationResult(-1, "")
        }

        return CompilationResult(0, pathToCompiled)
    }

    private fun executeCompilerInternal(project: Project) = executeCompiler(project, "")

    override fun executeCompiler(project: Project, args: Any): InvokeStatus {
        val pathToJavaFiles = project.saveOrRemoveToTmp(true)

        // Collect all Java files from the saved directory
        val javaFiles = pathToJavaFiles.split(" ").filter { it.endsWith(".java") }.map { File(it) }

        // Get the system Java compiler and initialize its components
        val compiler = ToolProvider.getSystemJavaCompiler()
        val diagnostics = DiagnosticCollector<JavaFileObject>()
        val manager = compiler.getStandardFileManager(diagnostics, null, null)
        val sources = manager.getJavaFileObjectsFromFiles(javaFiles)

        // Create the output directory if it doesn't already exist
        File(pathToCompiled).mkdirs()

        // Set up the compiler options and create the compilation task
        val options = mutableListOf("-d", pathToCompiled)
        val task = compiler.getTask(null, manager, diagnostics, options, null, sources)

        // Start the compiler task in a new thread
        val futureExitCode = threadPool.submit {
            task.call()
        }

        // Initialize flags for tracking the compilation process
        var hasTimeout = false
        var compilerWorkingTime: Long = -1

        try {
            // Start a timer to keep track of how long the compilation runs for
            val startTime = System.currentTimeMillis()
            futureExitCode.get(10L, TimeUnit.SECONDS)
            compilerWorkingTime = System.currentTimeMillis() - startTime
        } catch (_: TimeoutException) {
            // The compilation timed out
            hasTimeout = true
            futureExitCode.cancel(true)
        } finally {
            project.saveOrRemoveToTmp(false)
        }

        return JavacInvokeStatus(
            combinedOutput = diagnostics.diagnostics.joinToString("\n") { it.getMessage(Locale.getDefault()) },
            isCompileSuccess = diagnostics.diagnostics.none { it.kind == Diagnostic.Kind.ERROR },
            hasException = false,
            hasTimeout = hasTimeout,
            compilerExecTimeMillis = compilerWorkingTime,
            locations = diagnostics.diagnostics.filter { it.kind == Diagnostic.Kind.ERROR }.map {
                checkNotNull(
                    CompilerMessageLocation.create(
                        it.source.name,
                        line = it.lineNumber.toInt(),
                        column = it.columnNumber.toInt(),
                        lineContent = it.toString()
                    )
                )
            }
        )
    }
}
