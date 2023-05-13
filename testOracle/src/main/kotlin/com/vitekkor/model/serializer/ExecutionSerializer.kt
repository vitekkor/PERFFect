package com.vitekkor.model.serializer

import com.vitekkor.model.MeasurementResult
import kotlinx.serialization.KSerializer
import kotlinx.serialization.descriptors.SerialDescriptor
import kotlinx.serialization.descriptors.buildClassSerialDescriptor
import kotlinx.serialization.descriptors.element
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.encoding.encodeStructure

object ExecutionSerializer : KSerializer<MeasurementResult.Execution> {
    override val descriptor: SerialDescriptor = buildClassSerialDescriptor("Execution") {
        element<Double>("time")
        element<Long>("compileTime")
    }

    override fun deserialize(decoder: Decoder): MeasurementResult.Execution {
        TODO("Not yet implemented")
    }

    override fun serialize(encoder: Encoder, value: MeasurementResult.Execution) {
        encoder.encodeStructure(descriptor) {
            encodeDoubleElement(descriptor, 0, value.time)
            encodeLongElement(descriptor, 1, value.compileTime)
        }
    }
}
