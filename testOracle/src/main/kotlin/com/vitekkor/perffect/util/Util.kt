package com.vitekkor.perffect.util

import java.io.File
import java.io.InputStream

object Util {
    fun getResource(fileName: String): File = File(checkNotNull(this::class.java.getResource("/$fileName")).path)

    fun getResourceAsStream(fileName: String): InputStream =
        checkNotNull(this::class.java.getResourceAsStream("/$fileName"))
}
