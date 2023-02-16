package com.vitekkor.config

import com.sksamuel.hoplite.ConfigLoader
import com.sksamuel.hoplite.PropertySource
import com.vitekkor.config.properties.CompilerArgs

val CompilerArgs = ConfigLoader.builder()
    .addSource(PropertySource.resource("/test-oracle.yml", optional = true))
    .build()
    .loadConfigOrThrow<CompilerArgs>()
