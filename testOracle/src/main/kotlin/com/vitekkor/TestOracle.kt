package com.vitekkor

import com.vitekkor.client.CodeGeneratorClient
import com.vitekkor.compiler.BaseCompiler
import com.vitekkor.compiler.JavaCompiler
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.compiler.model.CompileStatus
import com.vitekkor.config.CompilerArgs
import com.vitekkor.model.MeasurementResult
import com.vitekkor.project.Language
import com.vitekkor.project.Project
import com.vitekkor.project.toProject
import mu.KotlinLogging.logger
import src.server.Server
import java.io.File
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
            val kotlinProject = kotlin.toProject(Language.KOTLIN)
            log.info("$KOTLIN_PROGRAM generated code: ${kotlin.text}")

            val java = client.generateJava(seed)
            val javaProject = java.toProject(Language.JAVA)
            log.info("$JAVA_PROGRAM generated code: ${java.text}")

            val (kotlinCompileStatus, kotlinCompileTime) =
                kotlinCompiler.tryToCompileWithStatusAndExecutionTime(kotlinProject)
            log.info("$KOTLIN_PROGRAM compileStatus: $kotlinCompileStatus; compileTime: $kotlinCompileTime")

            val (javaCompileStatus, javaCompileTime) =
                javaCompiler.tryToCompileWithStatusAndExecutionTime(javaProject)
            log.info("$JAVA_PROGRAM compileStatus: $javaCompileStatus; compileTime: $javaCompileTime")

            if (javaCompileStatus != CompileStatus.OK || kotlinCompileStatus != CompileStatus.OK) {
                log.error { "One of compilers finished with non-zero status code" }
                log.error { "$SEED investigate this with $seed" }
                continue
            }

            val javaRepeatCount = chooseNumberOfExecutions(javaCompiler, java)
            val kotlinRepeatCount = chooseNumberOfExecutions(kotlinCompiler, kotlin)

            val targetRepeatCount = maxOf(javaRepeatCount, kotlinRepeatCount)

            val newJavaProject = replaceJavaMainFun(java.text, targetRepeatCount).toProject(Language.JAVA)
            val newKotlinProject = replaceKotlinMainFun(kotlin.text, targetRepeatCount).toProject(Language.KOTLIN)

            val compiledJava = javaCompiler.tryToCompileWithStatusAndExecutionTime(newJavaProject)
            log.info("$JAVA_PROGRAM compileStatus: ${compiledJava.first}; compileTime: ${compiledJava.second}")

            val compiledKotlin = kotlinCompiler.tryToCompileWithStatusAndExecutionTime(newKotlinProject)
            log.info("$KOTLIN_PROGRAM compileStatus: ${compiledKotlin.first}; compileTime: ${compiledKotlin.second}")

            val kotlinExecTime =
                measureAverageExecutionTime(kotlinCompiler, newKotlinProject.mainClass, targetRepeatCount)
            val javaExecTime = measureAverageExecutionTime(javaCompiler, newJavaProject.mainClass, targetRepeatCount)

            log.info("$SEED $seed")
            log.info("$KOTLIN_PROGRAM average execution time - $kotlinExecTime")
            log.info("$JAVA_PROGRAM average execution time - $javaExecTime")

            val measurementResult = MeasurementResult(
                MeasurementResult.Execution(kotlinExecTime, kotlinProject),
                MeasurementResult.Execution(javaExecTime, javaProject),
                seed
            )
            compareExecutionTimes(measurementResult)
        }
    }

    private fun chooseNumberOfExecutions(compiler: BaseCompiler, program: Server.Program): Int {
        if (program.language == Language.KOTLIN.name.lowercase()) {
            var repeatCount = 10
            lateinit var project: Project
            do {
                compiler.cleanUp()
                project = replaceKotlinMainFun(program.text, repeatCount).toProject(Language.KOTLIN)
                val compiled = compiler.compile(project)
                val executionTime = compiler.getExecutionTime(compiled.pathToCompiled, mainClass = project.mainClass)
                if (executionTime.first.contains("Exception")) {
                    break
                }
                repeatCount *= 10
            } while (executionTime.second < 1000)
            log.info("$KOTLIN_PROGRAM execution time over 1s with $repeatCount. Program text: $project")
            compiler.cleanUp()
            return repeatCount
        }
        if (program.language == Language.JAVA.name.lowercase()) {
            var repeatCount = 10
            lateinit var project: Project
            do {
                compiler.cleanUp()
                project = replaceJavaMainFun(program.text, repeatCount).toProject(Language.JAVA)
                val compiled = compiler.compile(project)
                val executionTime = compiler.getExecutionTime(compiled.pathToCompiled, mainClass = project.mainClass)
                if (executionTime.first.contains("Exception")) {
                    break
                }
                repeatCount *= 10
            } while (executionTime.second < 1000)
            log.info("$JAVA_PROGRAM execution time over 1s with $repeatCount. Program text: $project")
            compiler.cleanUp()
            return repeatCount
        }
        throw UnsupportedOperationException("Support only Java and Kotlin")
    }

    private fun replaceKotlinMainFun(code: String, repeat: Int): String {
        var mainFunFound = false
        var curlyBraces = 0
        val currentMainFun = code.split("\n").filter {
            if (it.contains("fun main(args: Array<String>)")) {
                mainFunFound = true
                true
            } else if (mainFunFound) {
                if (it.contains("{")) {
                    curlyBraces++
                } else if (it.contains("}")) {
                    curlyBraces--
                }
                if (curlyBraces == 0) {
                    mainFunFound = false
                }
                true
            } else {
                false
            }
        }.joinToString("\n")
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        newMainFun.append("\n    repeat($repeat) {\n        try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(t: Throwable) {}\n    }\n}")
        return code.replace(currentMainFun, newMainFun.toString())
    }

    private fun replaceJavaMainFun(code: String, repeat: Int): String {
        var mainFunFound = false
        val currentMainFun = code.split("\n").filter {
            if (it.contains("static public final void main(String[] args)")) {
                mainFunFound = true
                true
            } else if (it.contains("interface Function0<R>")) {
                mainFunFound = false
                false
            } else {
                mainFunFound
            }
        }.dropLast(2).joinToString("\n")
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        newMainFun.append("\n    for (int javaIterationVariable = 1; javaIterationVariable <= $repeat; javaIterationVariable++) {\n    try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(Throwable t) {}\n}\n}")
        return code.replace(currentMainFun, newMainFun.toString())
    }

    private fun measureAverageExecutionTime(compiler: BaseCompiler, mainClass: String, executionCount: Int): Double {
        val path = File(compiler.pathToCompiled)
            .walkTopDown()
            .maxDepth(mainClass.split(".").size)
            .filter { it.isFile }
            .joinToString(":") { it.path }
        val totalTime = compiler.getExecutionTime(path, mainClass = mainClass).second
        return totalTime / executionCount.toDouble()
    }

    private fun compareExecutionTimes(measurementResult: MeasurementResult) {
        val percentage = measurementResult.kotlin.time / measurementResult.java.time
        if (percentage > CompilerArgs.percentageDelta) {
            log.warn { "Performance degradation detected" }
            // todo save projects
        }
    }

    companion object {
        private const val SEED = "[SEED]"
        private const val KOTLIN_PROGRAM = "[KOTLIN]"
        private const val JAVA_PROGRAM = "[JAVA]"
    }
}
