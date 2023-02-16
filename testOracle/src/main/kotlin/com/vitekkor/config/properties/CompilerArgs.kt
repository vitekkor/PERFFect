package com.vitekkor.config.properties

data class CompilerArgs(
    val pathToTmpDir: String,
    val jvmStdLibPaths: List<String> = listOf()
)
