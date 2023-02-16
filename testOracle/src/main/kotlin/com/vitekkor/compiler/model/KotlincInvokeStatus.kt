package com.vitekkor.compiler.model

import org.jetbrains.kotlin.cli.common.messages.CompilerMessageSourceLocation

class KotlincInvokeStatus(
    val combinedOutput: String,
    val isCompileSuccess: Boolean,
    val hasException: Boolean,
    val hasTimeout: Boolean,
    val compilerExecTimeInMlls: Long,
    val locations: List<CompilerMessageSourceLocation> = listOf()
) {
    fun hasCompilerCrash(): Boolean = hasTimeout || hasException

    fun hasCompilationError(): Boolean = !isCompileSuccess
}