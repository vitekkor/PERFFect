package com.vitekkor.project

internal fun getCommentSection(text: String) =
    text.lineSequence()
        .takeWhile { it.startsWith("//") || it.trim().isEmpty() }
        .joinToString("\n")
