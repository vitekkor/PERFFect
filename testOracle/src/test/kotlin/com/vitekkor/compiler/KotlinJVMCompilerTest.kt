package com.vitekkor.compiler

import com.vitekkor.project.Project
import org.junit.jupiter.api.Test
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class KotlinJVMCompilerTest {
    @Test
    fun compileProject() {
        val kotlinFile = File(checkNotNull(this::class.java.getResource("/Test.kt")).path)
        val project = Project.createFromCode(kotlinFile.readText())
        val compiler = KotlinJVMCompiler()
        val result = compiler.compile(project)
        assertEquals(0, result.status)
        val jar = File(result.pathToCompiled)
        assertTrue(jar.exists())
        jar.delete()
    }
}
