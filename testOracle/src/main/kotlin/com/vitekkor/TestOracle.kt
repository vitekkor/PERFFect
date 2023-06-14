package com.vitekkor

import com.vitekkor.client.CodeGeneratorClient
import com.vitekkor.compiler.BaseCompiler
import com.vitekkor.compiler.JavaCompiler
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.compiler.model.CompileStatus
import com.vitekkor.config.CompilerArgs
import com.vitekkor.model.MeasurementResult
import com.vitekkor.model.Stat
import com.vitekkor.perffect.util.BodySurgeon.replaceJavaMainFun
import com.vitekkor.perffect.util.BodySurgeon.replaceKotlinMainFun
import com.vitekkor.project.Language
import com.vitekkor.project.Project
import com.vitekkor.project.toProject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import mu.KotlinLogging.logger
import src.server.Server
import java.io.File
import java.time.Instant
import kotlin.random.Random
import kotlin.time.Duration
import kotlin.time.ExperimentalTime
import kotlin.time.measureTimedValue

val javaStat = Stat()
val kotlinStat = Stat()
suspend fun main() {
    Runtime.getRuntime().addShutdownHook(
        Thread {
            val timestamp = Instant.now()
            javaStat.percentOfIncorrectPrograms = (javaStat.totalNumberOfPrograms - javaStat.correctPrograms) /
                maxOf(javaStat.totalNumberOfPrograms.toDouble(), 1.0)
            kotlinStat.percentOfIncorrectPrograms = (kotlinStat.totalNumberOfPrograms - kotlinStat.correctPrograms) /
                maxOf(kotlinStat.totalNumberOfPrograms.toDouble(), 1.0)

            javaStat.averageGenerationTimeMs /= maxOf(javaStat.totalNumberOfPrograms, 1)
            kotlinStat.averageGenerationTimeMs /= maxOf(kotlinStat.totalNumberOfPrograms, 1)

            javaStat.averageCompileTimeMs /= maxOf(javaStat.correctPrograms, 1)
            javaStat.averageExecutionTimeMs /= maxOf(javaStat.correctPrograms, 1)
            kotlinStat.averageCompileTimeMs /= maxOf(kotlinStat.correctPrograms, 1)
            kotlinStat.averageExecutionTimeMs /= maxOf(kotlinStat.correctPrograms, 1)
            println(kotlinStat)
            println(javaStat)

            File(CompilerArgs.pathToResultsDir + "/$timestamp", "kotlinStat.json")
                .apply { parentFile.mkdirs() }
                .bufferedWriter().use {
                    it.write(Json.encodeToString(kotlinStat))
                }
            File(CompilerArgs.pathToResultsDir + "/$timestamp", "javaStat.json")
                .bufferedWriter().use {
                    it.write(Json.encodeToString(javaStat))
                }
        }
    )
    TestOracle().run()
}

class TestOracle {
    private val log = logger {}

    @OptIn(ExperimentalTime::class)
    suspend fun run() {
        log.info("Start test oracle")
        val client = CodeGeneratorClient.create()
        val kotlinCompiler = KotlinJVMCompiler()
        val javaCompiler = JavaCompiler()
        while (true) {
            val seed = Random.nextLong()
            kotlinCompiler.cleanUp()
            javaCompiler.cleanUp()
            try {
                log.info("$SEED $seed")
                val (kotlin, kotlinGenerationTime) = withTimeoutOrNull(Duration.minutes(2)) {
                    measureTimedValue { client.generateKotlin(seed) }
                }.also { if (it == null) log.warn { "$KOTLIN_PROGRAM timeout exceeded" } } ?: continue
                kotlinStat.totalNumberOfPrograms++
                kotlinStat.averageGenerationTimeMs += kotlinGenerationTime.inWholeMilliseconds

                val (java, javaGenerationTime) = withTimeoutOrNull(Duration.minutes(2)) {
                    measureTimedValue { client.generateJava(seed) }
                }.also { if (it == null) log.warn { "$JAVA_PROGRAM timeout exceeded" } } ?: continue
                javaStat.totalNumberOfPrograms++
                javaStat.averageGenerationTimeMs += javaGenerationTime.inWholeMilliseconds

                if (kotlin.text.isBlank()) {
                    log.error { "$KOTLIN_PROGRAM is empty - seed $seed" }
                }

                if (java.text.isBlank()) {
                    log.error { "$JAVA_PROGRAM is empty - seed $seed" }
                }

                if (kotlin.text.isBlank() || java.text.isBlank()) {
                    continue
                }

                val kotlinProject = kotlin.toProject(Language.KOTLIN)
                log.info("$KOTLIN_PROGRAM generated code: ${kotlin.text}")
                val javaProject = java.toProject(Language.JAVA)
                log.info("$JAVA_PROGRAM generated code: ${java.text}")

                val (kotlinCompileStatus, kotlinCompileTime) =
                    kotlinCompiler.tryToCompileWithStatusAndExecutionTime(kotlinProject)
                log.info("$KOTLIN_PROGRAM compileStatus: $kotlinCompileStatus; compileTime: $kotlinCompileTime")

                val (javaCompileStatus, javaCompileTime) =
                    javaCompiler.tryToCompileWithStatusAndExecutionTime(javaProject)
                log.info("$JAVA_PROGRAM compileStatus: $javaCompileStatus; compileTime: $javaCompileTime")

                if (kotlinCompileStatus == CompileStatus.OK) {
                    kotlinStat.averageCompileTimeMs += kotlinCompileTime
                    kotlinStat.correctPrograms++
                }

                if (javaCompileStatus == CompileStatus.OK) {
                    javaStat.averageCompileTimeMs += javaCompileTime
                    javaStat.correctPrograms++
                }

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
                    measureAverageExecutionTime(kotlinCompiler, newKotlinProject.mainClass)
                val javaExecTime =
                    measureAverageExecutionTime(javaCompiler, newJavaProject.mainClass)

                log.info("$SEED $seed")
                log.info("$KOTLIN_PROGRAM average execution time - $kotlinExecTime")
                log.info("$JAVA_PROGRAM average execution time - $javaExecTime")
                kotlinStat.averageExecutionTimeMs += kotlinExecTime
                javaStat.averageExecutionTimeMs += javaExecTime

                val measurementResult = MeasurementResult(
                    MeasurementResult.Execution(kotlinExecTime, kotlinProject, compiledKotlin.second),
                    MeasurementResult.Execution(javaExecTime, javaProject, compiledJava.second),
                    seed,
                    targetRepeatCount
                )
                compareExecutionTimes(measurementResult)
            } catch (e: Exception) {
                log.error("Unexpected exception occurred: ", e)
                log.error { "$SEED - $seed" }
            }
        }
    }

    private fun chooseNumberOfExecutions(compiler: BaseCompiler, program: Server.Program): Long {
        if (program.language == Language.KOTLIN.name.lowercase()) {
            var repeatCount = 10L
            lateinit var project: Project
            do {
                compiler.cleanUp()
                project = replaceKotlinMainFun(program.text, repeatCount).toProject(Language.KOTLIN)
                val compiled = compiler.compile(project)
                val executionTime = compiler.getExecutionTime(compiled.pathToCompiled, mainClass = project.mainClass)
                if (executionTime.first.contains("Exception")) {
                    break
                }
                repeatCount *= 10L
            } while (executionTime.second < 1000 && repeatCount > 0L)
            repeatCount /= 10L
            if (repeatCount < 0L) repeatCount = 9000000000000000000L
            log.info("$KOTLIN_PROGRAM execution time over 1s with $repeatCount. Program text: $project")
            compiler.cleanUp()
            return repeatCount
        }
        if (program.language == Language.JAVA.name.lowercase()) {
            var repeatCount = 10L
            lateinit var project: Project
            do {
                compiler.cleanUp()
                project = replaceJavaMainFun(program.text, repeatCount).toProject(Language.JAVA)
                val compiled = compiler.compile(project)
                val executionTime = compiler.getExecutionTime(compiled.pathToCompiled, mainClass = project.mainClass)
                if (executionTime.first.contains("Exception")) {
                    break
                }
                repeatCount *= 10L
            } while (executionTime.second < 1000 && repeatCount > 0L)
            repeatCount /= 10L
            if (repeatCount < 0L) repeatCount = 9000000000000000000L
            log.info("$JAVA_PROGRAM execution time over 1s with $repeatCount. Program text: $project")
            compiler.cleanUp()
            return repeatCount
        }
        throw UnsupportedOperationException("Support only Java and Kotlin")
    }

    private suspend fun compareExecutionTimes(measurementResult: MeasurementResult) {
        val percentage = measurementResult.kotlin.time / measurementResult.java.time
        if (percentage > CompilerArgs.percentageDelta) {
            log.warn { "Performance degradation detected" }
            measurementResult.kotlin.project.saveOrRemoveToDirectory(
                true,
                CompilerArgs.pathToResultsDir + "/${measurementResult.seed}"
            )
            measurementResult.java.project.saveOrRemoveToDirectory(
                true,
                CompilerArgs.pathToResultsDir + "/${measurementResult.seed}"
            )
            withContext(Dispatchers.IO) {
                File(CompilerArgs.pathToResultsDir + "/${measurementResult.seed}", "meta.json").bufferedWriter().use {
                    it.write(Json.encodeToString(measurementResult))
                }
            }
        }
    }

    companion object {
        private const val SEED = "[SEED]"
        private const val KOTLIN_PROGRAM = "[KOTLIN]"
        private const val JAVA_PROGRAM = "[JAVA]"

        fun measureAverageExecutionTime(compiler: BaseCompiler, mainClass: String): Double {
            val path = compiler.pathToCompiled
            val totalTime = compiler.getExecutionTime(path, mainClass = mainClass).second
            return totalTime.toDouble()
        }
    }
}
