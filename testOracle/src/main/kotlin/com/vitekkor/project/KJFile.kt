package com.vitekkor.project

import com.vitekkor.config.CompilerArgs
import com.vitekkor.util.WithLogger

// TODO rename
data class KJFile(val name: String, var text: String) {

    fun getLanguage(): Language {
        return when {
            name.endsWith(".java") -> Language.JAVA
            name.endsWith(".kt") -> Language.KOTLIN
            else -> Language.UNKNOWN
        }
    }

    override fun toString(): String =
        "// FILE: ${name.substringAfter(CompilerArgs.pathToTmpDir).substring(1)}\n\n$text"
}

internal class KJFileFactory(
    private val text: String,
    private val language: Language
) : WithLogger {

    fun createKJFiles(name: String = "Main"): KJFile {
        val pathToTmp = CompilerArgs.pathToTmpDir
        return text.let { code ->
            val fileName = "$pathToTmp/$name${language.extension}"
            KJFile(fileName, code)
        }
    }
}
