PERFFect
==========

PERFFect (Performance Error Finder based on Fuzzing testing) is a testing platform for finding performance issues
in compilers. The platform is based on an approach based on fuzzing testing.

Currently, PERFFect has been used to automated performance comparison of
two popular programming languages: Java, and Kotlin.


## Program Generation

The `codeGenerator` module is used to automatically generate random equivalent programs in Kotlin and Java.
It is based on the [Hepheastus](https://github.com/hephaestus-compiler-project/hephaestus/) framework,
which has been heavily redesigned to meet its intended goals.

The module can be run as a local script (mostly used for debugging), as well as a gRPC server.
Code generation is controlled by passing the initial value (seed) for the random number generator and selecting the target language.


## Test Oracle

The test oracle is written in Kotlin. It contains a gRPC client for receiving generated programs from the generator
and various tools for compiling and running the received programs.

It was decided to abandon compilation using native compilers, since the Kotlin language compiler uses the JVM to compile.
In addition, the built-in tools for compiling and running programs have greatly simplified the process of writing a test oracle.


# Requirements

* Python: 3.8+
* JVM

# Getting Started

## Usage

Set target JVM and Kotlin versions in `gradle.properties` file
```properties
kotlinVersion=1.5.31
jvmTarget=11
```

Run `run.sh` script
```shell
./run.sh build
```

or if you've already built testOracle.
```shell
./run.sh
```
