package com.vitekkor.perffect.util

import java.io.File

object Util {
    fun getResource(fileName: String): File = File(checkNotNull(this::class.java.getResource("/$fileName")).path)
}
