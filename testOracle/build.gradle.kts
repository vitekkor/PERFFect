import com.google.protobuf.gradle.id
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    kotlin("jvm") version "1.7.21"
    id("com.google.protobuf") version "0.9.2"
}

val grpcKotlinVersion = "1.3.0"
val grpcVersion = "1.47.0"
val protobufVersion = "3.21.2"
val kotlin_version = "1.7.21"

dependencies {
    implementation("io.grpc:grpc-kotlin-stub:$grpcKotlinVersion")
    implementation("io.grpc:grpc-protobuf:$grpcVersion")
    implementation("com.google.protobuf:protobuf-kotlin:$protobufVersion")
    implementation("org.apache.commons:commons-exec:1.3")
    implementation("commons-io:commons-io:2.7")
    implementation("io.github.microutils:kotlin-logging-jvm:3.0.5")
    implementation("com.sksamuel.hoplite:hoplite-core:2.7.1")
    implementation("com.sksamuel.hoplite:hoplite-yaml:2.7.1")

    implementation("org.jetbrains.kotlin:kotlin-stdlib:${kotlin_version}")
    implementation("org.jetbrains.kotlin:kotlin-stdlib-common:${kotlin_version}")
    implementation("org.jetbrains.kotlin:kotlin-compiler:${kotlin_version}")
    implementation("org.jetbrains.kotlin:kotlin-compiler-embeddable:${kotlin_version}")
    implementation("org.jetbrains.kotlin:kotlin-daemon-embeddable:${kotlin_version}")
    implementation("org.jetbrains.kotlin:kotlin-reflect:${kotlin_version}")

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

tasks.withType<KotlinCompile> {
    kotlinOptions.jvmTarget = "11"
}
