package com.vitekkor.client

import io.grpc.ManagedChannel
import io.grpc.ManagedChannelBuilder
import src.server.GeneratorGrpcKt
import src.server.Server
import src.server.generateRequest
import java.io.Closeable
import java.util.concurrent.TimeUnit

class CodeGeneratorClient(private val channel: ManagedChannel) : Closeable {

    private val stub: GeneratorGrpcKt.GeneratorCoroutineStub by lazy { GeneratorGrpcKt.GeneratorCoroutineStub(channel) }

    suspend fun generateKotlin(seed: Long): Server.Program {
        val request = generateRequest {
            this.seed = seed
        }
        return stub.generateKotlin(request)
    }

    suspend fun generateJava(seed: Long): Server.Program {
        val request = generateRequest {
            this.seed = seed
        }
        return stub.generateJava(request)
    }

    override fun close() {
        channel.shutdown().awaitTermination(5, TimeUnit.SECONDS)
    }

    companion object {
        fun create(host: String = "localhost", port: Int = 50051): CodeGeneratorClient {
            return CodeGeneratorClient(ManagedChannelBuilder.forAddress(host, port).usePlaintext().build())
        }
    }
}
