package com.vitekkor.perffect

import com.vitekkor.perffect.project.Language
import com.vitekkor.perffect.util.BodySurgeon
import com.vitekkor.perffect.util.Util
import org.junit.jupiter.api.Test
import java.io.File
import kotlin.test.assertEquals

internal class BodySergeonTest {
    @Test
    fun `should extract kotlin main funs properly`() {
        val samplesDir = Util.getResource("bodySergeonSamples/kotlin")
        val original = samplesDir.walkTopDown().filter { it.isFile && !it.name.contains("_main") }.toList()

        for (originalFile in original) {
            val extracted = BodySurgeon.extractKotlinMainFunction(originalFile.code()) + "\n"
            val expected = getMainFun(Language.KOTLIN, originalFile.nameWithoutExtension).code()
            assertEquals(expected, extracted)
        }
    }

    @Test
    fun `should extract java main funs properly`() {
        val samplesDir = Util.getResource("bodySergeonSamples/java")
        val original = samplesDir.walkTopDown().filter { it.isFile && !it.name.contains("_main") }.toList()

        for (originalFile in original) {
            val extracted = BodySurgeon.extractJavaMainFunction(originalFile.code()) + "\n"
            val expected = getMainFun(Language.JAVA, originalFile.nameWithoutExtension).code()
            assertEquals(expected, extracted)
        }
    }

    private fun File.code(): String = readText()

    private fun getMainFun(language: Language, name: String): File {
        return when (language) {
            Language.JAVA -> File(
                Util.getResource("bodySergeonSamples/java").path,
                "${name.removeSuffix(".java")}_main.java.txt"
            )

            Language.KOTLIN -> File(
                Util.getResource("bodySergeonSamples/kotlin").path,
                "${name.removeSuffix(".kt")}_main.kt.txt"
            )

            Language.UNKNOWN -> throw Error("UNKNOWN_LANGUAGE")
        }
    }
}
