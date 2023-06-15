package com.vitekkor.perffect.project

import com.vitekkor.perffect.config.CompilerArgs
import com.vitekkor.perffect.util.WithLogger

data class PerffectFile(val name: String, var text: String) {

    override fun toString(): String =
        "// FILE: ${name.substringAfter(CompilerArgs.pathToTmpDir).substring(1)}\n\n$text"
}

internal class KJFileFactory(
    private val text: String,
    private val language: Language
) : WithLogger {

    fun createKJFiles(name: String = "Main"): PerffectFile {
        val pathToTmp = CompilerArgs.pathToTmpDir
        return text.let { code ->
            val fileName = "$pathToTmp/$name${language.extension}"
            PerffectFile(fileName, code)
        }
    }
}
