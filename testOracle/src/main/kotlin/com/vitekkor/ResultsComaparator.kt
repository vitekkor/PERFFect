package com.vitekkor

import com.vitekkor.compiler.JavaCompiler
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.config.CompilerArgs
import com.vitekkor.project.Language
import com.vitekkor.project.toProject
import java.io.File
import kotlin.system.exitProcess

fun main() {
    val seed = 2444720093877148376
    val kotlinCompiler = KotlinJVMCompiler()
    val javaCompiler = JavaCompiler()
    kotlinCompiler.cleanUp()
    javaCompiler.cleanUp()

    val kotlin = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.kt").readText()
    val java = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.java").readText()

    val kotlinProject = kotlin.toProject(Language.KOTLIN)
    val javaProject = java.toProject(Language.JAVA)

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
