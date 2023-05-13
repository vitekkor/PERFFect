package com.vitekkor.model

import com.vitekkor.model.serializer.ExecutionSerializer
import com.vitekkor.project.Project
import kotlinx.serialization.Serializable

@Serializable
data class MeasurementResult(val kotlin: Execution, val java: Execution, val seed: Long, val repeatCount: Long) {
    @Serializable(with = ExecutionSerializer::class)
    data class Execution(val time: Double, val project: Project, val compileTime: Long)
}
