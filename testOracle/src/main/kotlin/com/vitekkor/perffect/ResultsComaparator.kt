package com.vitekkor.perffect

import com.vitekkor.perffect.compiler.JavaCompiler
import com.vitekkor.perffect.compiler.KotlinJVMCompiler
import com.vitekkor.perffect.config.CompilerArgs
import com.vitekkor.perffect.model.MeasurementResult
import com.vitekkor.perffect.project.Language
import com.vitekkor.perffect.project.toProject
import com.vitekkor.perffect.util.BodySurgeon
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import java.io.File
import kotlin.system.exitProcess

/**
 * Compare the execution times of Java and Kotlin programs.
 * Reads the necessary files from the file system, compiles the programs, measures their execution times,
 * and outputs the results to the console.
 */
fun main() {
    val seed = -8497514709130667753
    val kotlinCompiler = KotlinJVMCompiler()
    val javaCompiler = JavaCompiler()
    kotlinCompiler.cleanUp()
    javaCompiler.cleanUp()

    val kotlin = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.kt").readText()
    val java = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.java").readText()

    val metaJson = File(CompilerArgs.pathToResultsDir + "/$seed", "meta.json")
        .let { Json.decodeFromString<MeasurementResult>(it.readText()) }

    val kotlinProject = BodySurgeon.replaceKotlinMainFun(kotlin, metaJson.repeatCount).toProject(Language.KOTLIN)
    val javaProject = BodySurgeon.replaceJavaMainFun(java, metaJson.repeatCount).toProject(Language.JAVA)

    val compiledJava = javaCompiler.tryToCompileWithStatusAndExecutionTime(javaProject)

    val compiledKotlin = kotlinCompiler.tryToCompileWithStatusAndExecutionTime(kotlinProject)

    val kotlinExecTime = TestOracle.measureAverageExecutionTime(kotlinCompiler, kotlinProject.mainClass)
    val javaExecTime = TestOracle.measureAverageExecutionTime(javaCompiler, javaProject.mainClass)

    println("KOTLIN: compileTime - ${compiledKotlin.second}ms; executionTime - ${kotlinExecTime}ms")
    println("JAVA: compileTime - ${compiledJava.second}ms; executionTime - ${javaExecTime}ms")
    print("DIFF: compileTime - ${compiledKotlin.second.toDouble() / compiledJava.second.toDouble()}; ")
    println("executionTime - ${kotlinExecTime / javaExecTime}")
    exitProcess(0)
}
