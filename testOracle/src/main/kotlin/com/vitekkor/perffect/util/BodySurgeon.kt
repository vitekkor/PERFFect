package com.vitekkor.perffect.util

object BodySurgeon {
    fun replaceKotlinMainFun(code: String, repeat: Long): String {
        val currentMainFun = extractKotlinMainFunction(code)
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        val iter = getRepeatCountList(repeat)
        for (i in iter.size - 1 downTo 0) {
            newMainFun.append("\n    repeat(${iter[i]}) {\n")
        }
        newMainFun.append("        try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(t: Throwable) {}\n    }")
        for (i in iter) {
            newMainFun.append("\n}")
        }
        return code.replace(currentMainFun, newMainFun.toString())
    }

    fun replaceJavaMainFun(code: String, repeat: Long): String {
        val currentMainFun = extractJavaMainFunction(code)
        val firstCurlyBracket = currentMainFun.indexOf('{')
        val newMainFun = StringBuilder(currentMainFun.substring(0..firstCurlyBracket))
        val iter = getRepeatCountList(repeat)
        for (i in iter.size - 1 downTo 0) {
            val iterationVariableName = "javaIterationVariable_$i"
            newMainFun.append("\n    for (int $iterationVariableName = 1; $iterationVariableName <= ${iter[i]}; $iterationVariableName++) {\n")
        }
        newMainFun.append("    try {\n")
        newMainFun.append(currentMainFun.substring(firstCurlyBracket + 1))
        newMainFun.append(" catch(Throwable t) {}\n}")
        for (i in iter) {
            newMainFun.append("\n}")
        }
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

    private fun getRepeatCountList(repeat: Long): List<Long> {
        val iter = mutableListOf<Long>()
        var repeatCount = repeat
        do {
            val iteration = repeatCount / 1000000000
            if (iteration > 0) {
                iter.add(1000000000)
            } else if (repeatCount != 0L && repeatCount != 1L) {
                iter.add(repeatCount)
            }
            repeatCount /= 1000000000
        } while (repeatCount != 0L)
        return iter
    }
}
