package com.vitekkor

import com.vitekkor.client.CodeGeneratorClient
import com.vitekkor.compiler.JavaCompiler
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.project.Language
import com.vitekkor.project.toProject
import mu.KotlinLogging.logger
import kotlin.random.Random

suspend fun main() {
    TestOracle().run()
}

class TestOracle {
    private val log = logger {}
    suspend fun run() {
        log.info("Start test oracle")
        val client = CodeGeneratorClient.create()
        val kotlinCompiler = KotlinJVMCompiler()
        val javaCompiler = JavaCompiler()
        for (i in 1..10) {
            val seed = Random.nextLong()
            log.info("$SEED $seed")

            val kotlin = client.generateKotlin(seed)
            log.info("$KOTLIN_PROGRAM generated code: ${kotlin.text}")

            val java = client.generateJava(seed)
            log.info("$JAVA_PROGRAM - generated code: ${java.text}")

            val (kotlinCompileStatus, kotlinCompileTime) = kotlinCompiler.tryToCompileWithStatusAndExecutionTime(kotlin.toProject(Language.KOTLIN))
            log.info("$KOTLIN_PROGRAM compileStatus: $kotlinCompileStatus; compileTime: $kotlinCompileTime")

            val (javaCompileStatus, javaCompileTime) = javaCompiler.tryToCompileWithStatusAndExecutionTime(java.toProject(Language.JAVA))
            log.info("$JAVA_PROGRAM compileStatus: $javaCompileStatus; compileTime: $javaCompileTime")
        }
    }

    companion object {
        private const val SEED = "[SEED]"
        private const val KOTLIN_PROGRAM = "[KOTLIN]"
        private const val JAVA_PROGRAM = "[JAVA]"
    }
}
