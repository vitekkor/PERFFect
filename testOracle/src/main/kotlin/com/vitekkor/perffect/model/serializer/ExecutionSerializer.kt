package com.vitekkor.perffect.model.serializer

import com.vitekkor.perffect.model.MeasurementResult
import com.vitekkor.perffect.project.Language
import com.vitekkor.perffect.project.Project
import kotlinx.serialization.KSerializer
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.descriptors.buildClassSerialDescriptor
import kotlinx.serialization.descriptors.element
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.encoding.encodeStructure

object ExecutionSerializer : KSerializer<MeasurementResult.Execution> {
    @Serializable
    @SerialName("Execution")
    private data class ExecutionSurrogate(
        val time: Double,
        val compileTime: Long,
    )

    override val descriptor: SerialDescriptor = buildClassSerialDescriptor("Execution") {
        element<Double>("time")
        element<Long>("compileTime")
    }

    override fun deserialize(decoder: Decoder): MeasurementResult.Execution {
        val surrogate = decoder.decodeSerializableValue(ExecutionSurrogate.serializer())
        return MeasurementResult.Execution(
            surrogate.time,
            Project.createFromCode("package src\n", Language.KOTLIN),
            surrogate.compileTime
        )
    }

    override fun serialize(encoder: Encoder, value: MeasurementResult.Execution) {
        encoder.encodeStructure(descriptor) {
            encodeDoubleElement(descriptor, 0, value.time)
            encodeLongElement(descriptor, 1, value.compileTime)
        }
    }
}
