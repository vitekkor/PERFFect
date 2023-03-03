package com.vitekkor.compiler.model

import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation

sealed class InvokeStatus {

    abstract val combinedOutput: String

    abstract val isCompileSuccess: Boolean

    abstract val hasException: Boolean

    abstract val hasTimeout: Boolean

    abstract val compilerExecTimeMillis: Long

    abstract val locations: List<CompilerMessageSourceLocation>
    fun hasCompilationError(): Boolean = !isCompileSuccess
}

data class KotlincInvokeStatus(
    override val combinedOutput: String,
    override val isCompileSuccess: Boolean,
    override val hasException: Boolean,
    override val hasTimeout: Boolean,
    override val compilerExecTimeMillis: Long,
    override val locations: List<CompilerMessageSourceLocation> = listOf()
) : InvokeStatus() {
    fun hasCompilerCrash(): Boolean = hasTimeout || hasException
}

data class JavacInvokeStatus(
    override val combinedOutput: String,
    override val isCompileSuccess: Boolean,
    override val hasException: Boolean,
    override val hasTimeout: Boolean,
    override val compilerExecTimeMillis: Long,
    override val locations: List<CompilerMessageSourceLocation> = listOf()
) : InvokeStatus()
