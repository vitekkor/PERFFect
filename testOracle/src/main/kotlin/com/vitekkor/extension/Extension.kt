package com.vitekkor.extension

fun String.filterNotLines(cond: (String) -> Boolean): String =
    this.lines().filterNot { cond(it) }.joinToString("\n")
