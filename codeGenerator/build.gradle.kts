tasks.register("build") {
    finalizedBy("buildPython")
}

tasks.register("clean") {
    finalizedBy("cleanupPython")
}
tasks.register("buildPython", Exec::class.java) {
    commandLine("./build.sh")
}

tasks.register("cleanupPython", Exec::class.java) {
    commandLine("./clean.sh")
}
