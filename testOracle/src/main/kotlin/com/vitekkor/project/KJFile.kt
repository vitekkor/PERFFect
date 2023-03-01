package com.vitekkor.project

import com.vitekkor.config.CompilerArgs
import com.vitekkor.extension.filterNotLines
import com.vitekkor.util.WithLogger
import java.io.File

// TODO rename
data class KJFile(val name: String, var text: String) {

    fun getLanguage(): LANGUAGE {
        return when {
            name.endsWith(".java") -> LANGUAGE.JAVA
            name.endsWith(".kt") -> LANGUAGE.KOTLIN
            else -> LANGUAGE.UNKNOWN
        }
    }

    override fun toString(): String =
        "// FILE: ${name.substringAfter(CompilerArgs.pathToTmpDir).substring(1)}\n\n${text}"
}

internal class KJFileFactory(
    private val text: String,
    private val configuration: Header
) : WithLogger {

    fun createKJFiles(name: String = "tmp"): List<KJFile>? {
        try {
            val splitCode = splitCodeByFiles(text)
            val names = splitCode.map { code -> code.lines().find { it.startsWith(Directives.file) } ?: "" }
            val codeWithoutComments = splitCode.map { code -> code.filterNotLines { it.startsWith("// ") }.trim() }
            val pathToTmp = CompilerArgs.pathToTmpDir
            return if (names.any { it.isEmpty() }) codeWithoutComments.mapIndexed { i, code ->
                val fileName = "$pathToTmp/$name$i.kt"
                KJFile(fileName, code)
            }
            else names.zip(codeWithoutComments).map {
                val fileName = "$pathToTmp/${it.first.substringAfter(Directives.file)}"
                KJFile(fileName, it.second)
            }
        } catch (e: Throwable) {
            logger.error("Couldn't create KJFIle $text", e)
            return null
        }
    }

    private fun splitByFragments(text: String, splitter: String): List<String> {
        val lines = text.lines()
        val fragments = mutableListOf<String>()
        val firstCommentsSection = lines.takeWhile { it.trim().isEmpty() || it.startsWith("//") }
        if (firstCommentsSection.any { it.startsWith(splitter) }) {
            val curFragment = mutableListOf<String>()
            for (i in firstCommentsSection.size until lines.size) {
                val line = lines[i]
                if (!line.startsWith(splitter)) {
                    curFragment.add(line)
                } else {
                    fragments.add(curFragment.joinToString("\n"))
                    curFragment.clear()
                    curFragment.add(line)
                }
            }
            fragments.add(curFragment.joinToString("\n"))
        } else fragments.add(text.lines().filterNot { it.startsWith("// ") }.joinToString("\n"))
        if (configuration.withDirectives.contains(Directives.coroutinesDirective)) handleCoroutines(fragments)
        val firstFragment = firstCommentsSection.joinToString("\n") + "\n" + fragments[0]
        return listOf(firstFragment) + fragments.subList(1, fragments.size)
    }

    private fun handleCoroutines(fragments: MutableList<String>) {
        val coroutinesPackage = "COROUTINES_PACKAGE"
        val ktCoroutinesPackage = "kotlin.coroutines"
        val helpersImportDirective = "import helpers.*"
        val nameOfHelpersFile = "CoroutineUtil.kt"
        val pathToHelpersFile = "${CompilerArgs.pathToTmpDir}/lib/CoroutineUtil.kt"
        val textOfFile = "${Directives.file}$nameOfHelpersFile\n${File(pathToHelpersFile).readText()}"
        for (i in fragments.indices) {
            fragments[i] = fragments[i]
                .replace(coroutinesPackage, ktCoroutinesPackage)
                .replace("import kotlin.coroutines.experimental", "import kotlin.coroutines")

        }
        if (fragments.any { it.contains(helpersImportDirective) }) fragments.add(textOfFile)
    }

    private fun splitCodeByFiles(text: String): List<String> {
        return splitByFragments(text, Directives.file)
    }

}