package com.vitekkor.compiler

import com.vitekkor.project.Language
import com.vitekkor.project.Project
import org.junit.jupiter.api.Test
import java.io.File
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class JavaCompilerTest {

    @Test
    fun compileProject() {
        val javaFile = File(checkNotNull(this::class.java.getResource("/Test.java")).path)
        val project = Project.createFromCode(javaFile.readText(), Language.JAVA)
        val compiler = JavaCompiler()
        val result = compiler.compile(project)
        assertEquals(0, result.status)
        val jar = File(result.pathToCompiled)
        assertTrue(jar.exists())
        val files = jar.walkTopDown().maxDepth(3).toList().drop(2)
        assertTrue { files.all { it.path.contains("com/vitekkor") } }
        assertTrue { files.count { it.extension == "class" } == 21 }
        jar.deleteRecursively()
    }
}
