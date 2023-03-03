package com.vitekkor.config

import com.sksamuel.hoplite.ConfigLoader
import com.sksamuel.hoplite.PropertySource
import com.vitekkor.config.properties.CompilerArgs

data class MainConfig(val compilerArgs: CompilerArgs)

private val mainConfig = ConfigLoader.builder()
    .addSource(PropertySource.resource("/test-oracle.yml", optional = true))
    .addSource(PropertySource.resource("/kotlin.yml", optional = true))
    .build()
    .loadConfigOrThrow<MainConfig>()

val CompilerArgs = mainConfig.compilerArgs
