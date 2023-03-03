package com.vitekkor.project

import src.server.Server

internal fun getCommentSection(text: String) =
    text.lineSequence()
        .takeWhile { it.startsWith("//") || it.trim().isEmpty() }
        .joinToString("\n")

fun Server.Program.toProject(language: LANGUAGE): Project {
    return Project.createFromCode(text, language)
}
