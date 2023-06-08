package com.vitekkor.model

import kotlinx.serialization.Serializable

@Serializable
data class Stat(
    var totalNumberOfPrograms: Long = 0L,
    var correctPrograms: Long = 0L,
    var percentOfIncorrectPrograms: Double = 0.0,
    var averageCompileTime: Double = 0.0,
    var averageGenerationTime: Double = 0.0,
    var averageExecutionTime: Double = 0.0,
)
