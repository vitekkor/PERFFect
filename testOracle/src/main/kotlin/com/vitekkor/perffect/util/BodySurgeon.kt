package com.vitekkor.perffect.util

/**
 * Provides methods to modify the main functions of Kotlin and Java programs by adding loops to repeat the program execution.
 */
object BodySurgeon {

    /**
     * Replaces the main function of a Kotlin program with a modified version that executes the program multiple times using loops.
     * @param code the source code of the program
     * @param repeat the number of times the program should be executed
     * @return the modified source code of the program
     */
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

    /**
     * Replaces the main function of a Java program with a modified version that executes the program multiple times using loops.
     * @param code the source code of the program
     * @param repeat the number of times the program should be executed
     * @return the modified source code of the program
     */
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

    /**
     * Extracts the main function from a Kotlin program.
     * @param code the source code of the program
     * @return the main function as a string
     */
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

    /**
     * Extracts the main function from a Java program.
     * @param code the source code of the program
     * @return the main function as a string
     */
    fun extractJavaMainFunction(code: String): String {
        var mainFunFound = false
        var curlyBraces = 0
        val currentMainFun = code.split("\n").filter {
            if (it.contains("static public final void main(String[] args)")) {
                mainFunFound = true
                true
            } else if (mainFunFound) {
                curlyBraces += it.count { char -> char == '{' }
                curlyBraces -= it.count { char -> char == '}' }
                if (curlyBraces == -1) {
                    mainFunFound = false
                }
                true
            } else {
                false
            }
        }.joinToString("\n")
        return currentMainFun
    }

    /**
     * Returns a list of numbers that, when multiplied together, add up to the given repeat count.
     * Used to split the repeat count into smaller chunks for easier processing.
     * @param repeat the number of times the program should be executed
     * @return a list of numbers that add up to the repeat count
     */
    private fun getRepeatCountList(repeat: Long): List<Long> {
        val iter = mutableListOf<Long>()
        var repeatCount = repeat
        do {
            val iteration = repeatCount / 1000000000 // Split the repeat count into chunks of 1 billion or less
            if (iteration > 0) {
                iter.add(1000000000) // Add the chunk to the list if it's equal to 1 billion
            } else if (repeatCount != 0L && repeatCount != 1L) {
                iter.add(repeatCount) // Add the last chunk to the list if it's less than 1 billion and not equal to 0 or 1
            }
            repeatCount /= 1000000000
        } while (repeatCount != 0L)
        return iter
    }
}
