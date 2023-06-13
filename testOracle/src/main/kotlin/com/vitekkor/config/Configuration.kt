package com.vitekkor.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory
import com.fasterxml.jackson.module.kotlin.registerKotlinModule
import com.vitekkor.config.properties.CompilerArgs
import com.vitekkor.perffect.util.Util

data class MainConfig(val compilerArgs: CompilerArgs)

private val mapper = ObjectMapper(YAMLFactory()).registerKotlinModule()

val CompilerArgs = mapper.readValue(Util.getResourceAsStream("test-oracle.yml"), MainConfig::class.java).compilerArgs
