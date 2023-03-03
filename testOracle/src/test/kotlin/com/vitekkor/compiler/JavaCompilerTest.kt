package com.vitekkor.compiler

import com.vitekkor.project.LANGUAGE
import com.vitekkor.project.Project
import org.junit.jupiter.api.Test
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class JavaCompilerTest {

    @Test
    fun compileProject() {
        val javaFile = File(checkNotNull(this::class.java.getResource("/Test.java")).path)
        val project = Project.createFromCode(javaFile.readText(), LANGUAGE.JAVA)
        val compiler = JavaCompiler()
        val result = compiler.compile(project)
        assertEquals(0, result.status)
        val jar = File(result.pathToCompiled)
        assertTrue(jar.exists())
        jar.delete()
    }
}
