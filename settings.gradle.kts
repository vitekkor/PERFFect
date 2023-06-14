rootProject.name = "perffect"
include("testOracle")
include("codeGenerator")

pluginManagement {
    val kotlinVersion: String by settings
    resolutionStrategy {
        eachPlugin {
            if (requested.id.id == "org.jetbrains.kotlin.jvm" || requested.id.id == "org.jetbrains.kotlin.plugin.serialization") {
                useVersion(kotlinVersion)
            }
        }
    }
}
