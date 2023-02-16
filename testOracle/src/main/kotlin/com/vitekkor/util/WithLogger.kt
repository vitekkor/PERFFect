package com.vitekkor.util

import mu.KotlinLogging.logger

interface WithLogger {
    val logger
        get() = logger {}
}