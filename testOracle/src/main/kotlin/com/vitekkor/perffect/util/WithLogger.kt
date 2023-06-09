package com.vitekkor.perffect.util

import mu.KLogger
import mu.KotlinLogging.logger

interface WithLogger {
    val logger: KLogger
        get() = logger(javaClass.name)
}
