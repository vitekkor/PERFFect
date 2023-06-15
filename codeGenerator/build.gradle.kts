tasks.register("build") {
    group = "build"
    finalizedBy("buildPython")
}

tasks.register("clean") {
    group = "build"
    finalizedBy("cleanupPython")
}
tasks.register("buildPython", Exec::class.java) {
    group = "build"
    commandLine("./build.sh")
}

tasks.register("cleanupPython", Exec::class.java) {
    group = "build"
    commandLine("./clean.sh")
}

tasks.register("pyFormat", Exec::class.java) {
    group = "formatting"
    commandLine("./format.sh")
}
