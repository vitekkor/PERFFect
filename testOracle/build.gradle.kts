import com.google.protobuf.gradle.id
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm")
    id("com.google.protobuf") version "0.9.2"
    id("org.jlleitschuh.gradle.ktlint") version "10.2.0"
    kotlin("plugin.serialization")
}

ktlint {
    filter {
        exclude { element -> element.file.path.contains("generated/") }
    }
}

val grpcKotlinVersion = "1.3.0"
val grpcVersion = "1.47.0"
val protobufVersion = "3.21.7"
val kotlinVersion: String by project

val libraries = listOf(
    "org.jetbrains.kotlin:kotlin-stdlib-jdk8:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-stdlib-jdk7:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-stdlib:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-stdlib-common:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-test:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-test-common:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-script-runtime:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-test-annotations-common:$kotlinVersion",
    "org.jetbrains.kotlin:kotlin-reflect:$kotlinVersion"
)

val toCopy: Configuration by configurations.creating

configurations.all {
    resolutionStrategy.eachDependency {
        if (requested.name.contains("kotlin-stdlib")) {
            useVersion(kotlinVersion)
        }
    }
}

dependencies {
    implementation("io.grpc:grpc-kotlin-stub:$grpcKotlinVersion")
    implementation("io.grpc:grpc-protobuf:$grpcVersion")
    implementation("com.google.protobuf:protobuf-kotlin:$protobufVersion")
    implementation("io.grpc:grpc-okhttp:1.53.0")
    implementation("org.apache.commons:commons-exec:1.3")
    implementation("commons-io:commons-io:2.7")
    implementation("io.github.microutils:kotlin-logging-jvm:3.0.5")
    implementation("ch.qos.logback:logback-classic:1.4.6")
    implementation("com.sksamuel.hoplite:hoplite-core:2.7.1")
    implementation("com.sksamuel.hoplite:hoplite-yaml:2.7.1")

    implementation("org.jetbrains.kotlin:kotlin-stdlib:$kotlinVersion")
    implementation("org.jetbrains.kotlin:kotlin-stdlib-common:$kotlinVersion")
    implementation("org.jetbrains.kotlin:kotlin-compiler:$kotlinVersion")
    implementation("org.jetbrains.kotlin:kotlin-compiler-embeddable:$kotlinVersion")
    implementation("org.jetbrains.kotlin:kotlin-daemon-embeddable:$kotlinVersion")
    implementation("org.jetbrains.kotlin:kotlin-reflect:$kotlinVersion")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.5.2") // 1.5.2 for kotlin 1.5.31
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.3.0") // 1.3.0 for kotlin 1.5.31

    // implementation("com.pinterest:ktlint:0.48.2")

    libraries.map {
        toCopy(it)
    }

    testImplementation(kotlin("test"))
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:$protobufVersion"
    }
    plugins {
        id("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:$grpcVersion"
        }
        id("grpckt") {
            artifact = "io.grpc:protoc-gen-grpc-kotlin:$grpcKotlinVersion:jdk8@jar"
        }
    }
    generateProtoTasks {
        all().forEach {
            it.plugins {
                id("grpc")
                id("grpckt")
            }
            it.builtins {
                id("kotlin")
            }
        }
    }
}

sourceSets {
    main {
        proto {
            srcDir("../protobuf")
        }
    }
}

tasks.test {
    useJUnitPlatform()
}

val downloadStdLib by tasks.creating(Copy::class.java) {
    group = "build"
    if (!file("files/lib/kotlin-stdlib-$kotlinVersion.jar").exists()) {
        from(toCopy)
        into("${project.rootDir.path}/files/lib")
    }
}

val cleanUpStdLib by tasks.creating(Task::class.java) {
    group = "build"
    outputs.upToDateWhen { false }
    doLast {
        File("files/lib/").deleteRecursively()
    }
}

val provideKotlinVersion: Task by tasks.creating {
    group = "build"
    outputs.upToDateWhen { false }
    doLast {
        project.sourceSets.main {
            File(resources.srcDirs.first().path + "/kotlin.yml").apply {
                if (exists()) delete()
                createNewFile()
                writeText("compilerArgs:\n  kotlinVersion: \"$kotlinVersion\"")
            }
        }
    }
}

val cleanKotlinVersion by tasks.creating(Task::class.java) {
    group = "build"
    doLast {
        project.sourceSets.main {
            File(resources.srcDirs.first().path + "/kotlin.yml").delete()
        }
    }
}
tasks.withType<KotlinCompile> {
    kotlinOptions.jvmTarget = project.property("jvmTarget") as String
    dependsOn(downloadStdLib)
    dependsOn(provideKotlinVersion)
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(project.property("jvmTarget") as String))
    }
}

tasks["clean"].finalizedBy(cleanUpStdLib).finalizedBy(cleanKotlinVersion)

tasks.jar {
    manifest.attributes["Main-Class"] = "com.vitekkor.TestOracleKt"
    val dependencies = configurations
        .runtimeClasspath
        .get()
        .map(::zipTree)
    from(dependencies)
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}
