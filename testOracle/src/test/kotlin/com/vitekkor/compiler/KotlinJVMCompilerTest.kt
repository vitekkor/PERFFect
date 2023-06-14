package com.vitekkor.compiler

import com.vitekkor.perffect.compiler.KotlinJVMCompiler
import com.vitekkor.perffect.project.Language
import com.vitekkor.perffect.project.Project
import org.junit.jupiter.api.Test
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class KotlinJVMCompilerTest {
    @Test
    fun compileProject() {
        val kotlinFile = File(checkNotNull(this::class.java.getResource("/Test.kt")).path)
        val project = Project.createFromCode(kotlinFile.readText(), Language.KOTLIN)
        val compiler = KotlinJVMCompiler()
        compiler.cleanUp()
        val result = compiler.compile(project)
        assertEquals(0, result.status)
        val jar = File(result.pathToCompiled)
        assertTrue(jar.exists())
        val files = jar.walkTopDown().maxDepth(3).toList()
        assertTrue { files.count { it.path.contains("com/vitekkor") } == 39 }
        assertTrue { files.count { it.path.contains("META-INF") } == 2 }
        assertTrue { files.count { it.extension == "class" } == 38 }
        jar.deleteRecursively()
    }
}
