package com.vitekkor.project

import src.server.Server

internal fun getCommentSection(text: String) =
    text.lineSequence()
        .takeWhile { it.startsWith("//") || it.trim().isEmpty() }
        .joinToString("\n")

fun Server.Program.toProject(): Project {
    return Project.createFromCode(text)
}
