package com.vitekkor.perffect.project

import src.server.Server

fun Server.Program.toProject(language: Language): Project {
    return Project.createFromCode(text, language)
}

fun String.toProject(language: Language): Project {
    return Project.createFromCode(this, language)
}

val Project.text: String
    get() = files.joinToString("\n")
