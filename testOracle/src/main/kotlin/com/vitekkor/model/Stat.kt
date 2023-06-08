package com.vitekkor.model

import kotlinx.serialization.Serializable

@Serializable
data class Stat(
    var totalNumberOfPrograms: Long = 0L,
    var correctPrograms: Long = 0L,
    var percentOfIncorrectPrograms: Double = 0.0,
    var averageCompileTimeMs: Double = 0.0,
    var averageGenerationTimeMs: Double = 0.0,
    var averageExecutionTimeMs: Double = 0.0,
)
