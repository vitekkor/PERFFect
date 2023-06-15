package com.vitekkor.perffect.project

import com.vitekkor.perffect.config.CompilerArgs
import java.io.File

class Project(
    var files: List<PerffectFile>,
    val language: Language = Language.KOTLIN,
    val `package`: String
) {

    val mainClass: String
        get() = `package` + "." + if (language == Language.KOTLIN) "MainKt" else "Main"

    constructor(file: PerffectFile, language: Language, `package`: String) : this(listOf(file), language, `package`)

    companion object {

        private val packageRegex = "package (.*)".toRegex()
        fun createFromCode(code: String, language: Language): Project {
            val file = KJFileFactory(code, language).createKJFiles()
            val `package` = checkNotNull(packageRegex.find(code)?.value).removePrefix("package").removeSuffix(";")
            return Project(file, language, `package`)
        }
    }

    fun saveOrRemoveToDirectory(trueSaveFalseDelete: Boolean, directory: String): String {
        files.forEach {
            val name = it.name.substringAfterLast('/')
            val fullDir = directory +
                if (it.name.contains("/")) {
                    "/${it.name.substringBeforeLast('/')}"
                } else {
                    ""
                }
            val fullName = "$fullDir/$name"
            if (trueSaveFalseDelete) {
                File(fullDir).mkdirs()
                File(fullName).writeText(it.text)
            } else {
                val createdDirectories = it.name.substringAfter(directory).substringBeforeLast('/')
                if (createdDirectories.trim().isNotEmpty()) {
                    File("$directory$createdDirectories").deleteRecursively()
                } else {
                    File(fullName).delete()
                }
            }
        }
        return files.joinToString(" ") { it.name }
    }

    fun saveOrRemoveToTmp(trueSaveFalseDelete: Boolean): String {
        files.forEach {
            if (trueSaveFalseDelete) {
                File(it.name.substringBeforeLast("/")).mkdirs()
                File(it.name).writeText(it.text)
            } else {
                val createdDirectories = it.name.substringAfter(CompilerArgs.pathToTmpDir).substringBeforeLast('/')
                if (createdDirectories.trim().isNotEmpty()) {
                    File("${CompilerArgs.pathToTmpDir}$createdDirectories").deleteRecursively()
                } else {
                    File(it.name).delete()
                }
            }
        }
        return files.joinToString(" ") { it.name }
    }

    fun copy(): Project {
        return Project(files.map { it.copy() }, language, `package`)
    }

    override fun toString(): String = files.joinToString("\n\n") {
        it.name + "\n" + it.text
    }
}
