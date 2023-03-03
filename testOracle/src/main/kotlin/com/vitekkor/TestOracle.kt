package com.vitekkor

import com.vitekkor.client.CodeGeneratorClient
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.project.Language
import com.vitekkor.project.toProject
import kotlin.random.Random

suspend fun main() {
    TestOracle().run()
}

class TestOracle {
    suspend fun run() {
        val client = CodeGeneratorClient.create()
        val compiler = KotlinJVMCompiler()
        for (i in 1..10) {
            val seed = Random.nextLong()
            val kotlin = client.generateKotlin(seed)
            val java = client.generateJava(seed)
            val (kotlinCompileStatus, kotlinCompileTime) = compiler.tryToCompileWithStatusAndExecutionTime(kotlin.toProject(Language.KOTLIN))
        }
    }
}
