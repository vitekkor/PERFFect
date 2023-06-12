package com.vitekkor

import com.vitekkor.compiler.JavaCompiler
import com.vitekkor.compiler.KotlinJVMCompiler
import com.vitekkor.config.CompilerArgs
import com.vitekkor.perffect.util.BodySurgeon
import com.vitekkor.project.Language
import com.vitekkor.project.Project
import com.vitekkor.project.toProject
import java.io.File
import kotlin.system.exitProcess

fun main() {
    val seed = 5335769039710021543
    val repeatCount: Long = Int.MAX_VALUE.toLong()
    val withRepeat = true
    val kotlinCompiler = KotlinJVMCompiler()
    val javaCompiler = JavaCompiler()
    kotlinCompiler.cleanUp()
    javaCompiler.cleanUp()

    val kotlin = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.kt").readText()
    val java = File(CompilerArgs.pathToResultsDir + "/$seed", CompilerArgs.pathToTmpDir + "/Main.java").readText()

    val kotlinProject: Project
    val javaProject: Project

    if (withRepeat) {
        kotlinProject = BodySurgeon.replaceKotlinMainFun(kotlin, repeatCount).toProject(Language.KOTLIN)
        javaProject = BodySurgeon.replaceJavaMainFun(java, repeatCount).toProject(Language.JAVA)
    } else {
        kotlinProject = kotlin.toProject(Language.KOTLIN)
        javaProject = java.toProject(Language.JAVA)
    }

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
