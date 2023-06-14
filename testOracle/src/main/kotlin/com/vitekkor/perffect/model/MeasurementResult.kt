package com.vitekkor.perffect.model

import com.vitekkor.perffect.model.serializer.ExecutionSerializer
import com.vitekkor.perffect.project.Project
import kotlinx.serialization.Serializable

@Serializable
data class MeasurementResult(val kotlin: Execution, val java: Execution, val seed: Long, val repeatCount: Long) {
    @Serializable(with = ExecutionSerializer::class)
    data class Execution(val time: Double, val project: Project, val compileTime: Long)
}
