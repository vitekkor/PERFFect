import com.google.protobuf.gradle.id
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm")
    id("com.google.protobuf") version "0.9.2"
}

val grpcKotlinVersion = "1.3.0"
val grpcVersion = "1.47.0"
val protobufVersion = "3.21.2"
val kotlinVersion: String by project


val libraries = listOf(
    "org.jetbrains.kotlin:kotlin-stdlib-jdk8:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-stdlib-jdk7:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-stdlib:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-stdlib-common:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-test:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-test-common:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-script-runtime:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-test-annotations-common:${kotlinVersion}",
    "org.jetbrains.kotlin:kotlin-reflect:${kotlinVersion}"
)

val toCopy: Configuration by configurations.creating

dependencies {
    implementation("io.grpc:grpc-kotlin-stub:$grpcKotlinVersion")
    implementation("io.grpc:grpc-protobuf:$grpcVersion")
    implementation("com.google.protobuf:protobuf-kotlin:$protobufVersion")
    implementation("org.apache.commons:commons-exec:1.3")
    implementation("commons-io:commons-io:2.7")
    implementation("io.github.microutils:kotlin-logging-jvm:3.0.5")
    implementation("com.sksamuel.hoplite:hoplite-core:2.7.1")
    implementation("com.sksamuel.hoplite:hoplite-yaml:2.7.1")

    implementation("org.jetbrains.kotlin:kotlin-stdlib:${kotlinVersion}")
    implementation("org.jetbrains.kotlin:kotlin-stdlib-common:${kotlinVersion}")
    implementation("org.jetbrains.kotlin:kotlin-compiler:${kotlinVersion}")
    implementation("org.jetbrains.kotlin:kotlin-compiler-embeddable:${kotlinVersion}")
    implementation("org.jetbrains.kotlin:kotlin-daemon-embeddable:${kotlinVersion}")
    implementation("org.jetbrains.kotlin:kotlin-reflect:${kotlinVersion}")

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
    if (!file("files/lib/kotlin-stdlib-${kotlinVersion}.jar").exists()) {
        val librariesToCopy = configurations.runtimeClasspath.get().allDependencies.map { toCopy.files(it) }
        from(librariesToCopy)
        into("files/lib")
    }
}

val cleanUpStdLib by tasks.creating(Delete::class.java) {
    delete("files/lib/")
}

tasks.withType<KotlinCompile> {
    kotlinOptions.jvmTarget = "11"
    dependsOn(downloadStdLib)
}

tasks["clean"].finalizedBy(cleanUpStdLib)
