package com.vitekkor.perffect.config.properties

data class CompilerArgs(
    val pathToTmpDir: String,
    val jvmStdLibBasePath: String,
    val kotlinVersion: String,
    val percentageDelta: Double,
    val pathToResultsDir: String
) {
    val jvmStdLibPaths: List<String> = listOf(
        "kotlin-stdlib",
        "kotlin-stdlib-common",
        "kotlin-test",
        "kotlin-test-common",
        "kotlin-reflect",
        "kotlin-stdlib-jdk8",
        "kotlin-stdlib-jdk7"
    ).map { "$jvmStdLibBasePath/$it-$kotlinVersion.jar" }

    fun getAnnotationsPath(version: String): String {
        return "$jvmStdLibBasePath/annotations-$version.jar"
    }
}
