package com.vitekkor.perffect.util

object BodySurgeon {
    fun replaceKotlinMainFun(code: String, repeat: Long): String {
        val currentMainFun = extractKotlinMainFunction(code)
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        newMainFun.append("\n    repeat($repeat) {\n        try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(t: Throwable) {}\n    }\n}")
        return code.replace(currentMainFun, newMainFun.toString())
    }

    fun replaceJavaMainFun(code: String, repeat: Long): String {
        val currentMainFun = extractJavaMainFunction(code)
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        newMainFun.append("\n    for (int javaIterationVariable = 1; javaIterationVariable <= $repeat; javaIterationVariable++) {\n    try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(Throwable t) {}\n}\n}")
        return code.replace(currentMainFun, newMainFun.toString())
    }

    fun extractKotlinMainFunction(code: String): String {
        var mainFunFound = false
        var curlyBraces = 0
        val currentMainFun = code.split("\n").filter {
            if (it.contains("fun main(args: Array<out String>)")) {
                mainFunFound = true
                true
            } else if (mainFunFound) {
                curlyBraces += it.count { char -> char == '{' }
                curlyBraces -= it.count { char -> char == '}' }
                if (curlyBraces == 0) {
                    mainFunFound = false
                }
                true
            } else {
                false
            }
        }.joinToString("\n")
        return currentMainFun
    }

    fun extractJavaMainFunction(code: String): String {
        var mainFunFound = false
        val currentMainFun = code.split("\n").filter {
            if (it.contains("static public final void main(String[] args)")) {
                mainFunFound = true
                true
            } else if (it.contains("interface Function0<R>")) {
                mainFunFound = false
                false
            } else {
                mainFunFound
            }
        }.dropLast(2).joinToString("\n")
        return currentMainFun
    }
}
