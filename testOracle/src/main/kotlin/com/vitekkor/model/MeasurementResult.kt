package com.vitekkor.model

import com.vitekkor.project.Project

data class MeasurementResult(val kotlin: Execution, val java: Execution, val seed: Long) {
    data class Execution(val time: Double, val project: Project)
}
