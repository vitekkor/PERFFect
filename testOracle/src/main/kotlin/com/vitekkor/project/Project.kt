package com.vitekkor.project

import com.vitekkor.config.CompilerArgs
import org.jetbrains.kotlin.cli.common.arguments.CommonCompilerArguments
import org.jetbrains.kotlin.cli.common.arguments.K2JSCompilerArguments
import org.jetbrains.kotlin.cli.common.arguments.K2JVMCompilerArguments
import org.jetbrains.kotlin.cli.js.K2JSCompiler
import org.jetbrains.kotlin.cli.jvm.K2JVMCompiler
import java.io.File

class Project(
    var configuration: Header,
    var files: List<KJFile>,
    val language: LANGUAGE = LANGUAGE.KOTLIN
) {

    constructor(configuration: Header, file: KJFile, language: LANGUAGE) : this(configuration, listOf(file), language)

    companion object {
        fun createFromCode(code: String): Project {
            val configuration = Header.createHeader(getCommentSection(code))
            val files = KJFileFactory(code, configuration).createKJFiles() ?: return Project(configuration, listOf())
            val language =
                when {
                    files.any { it.getLanguage() == LANGUAGE.UNKNOWN } -> LANGUAGE.UNKNOWN
                    files.any { it.getLanguage() == LANGUAGE.JAVA } -> LANGUAGE.KJAVA
                    else -> LANGUAGE.KOTLIN
                }
            return Project(configuration, files, language)
        }
    }

    fun addFile(file: KJFile): List<KJFile> {
        files = files + listOf(file)
        return files
    }

    fun removeFile(file: KJFile): List<KJFile> {
        files = files.getAllWithout(file)
        return files
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

    fun moveAllCodeInOneFile() =
        StringBuilder().apply {
            append(configuration.toString());
            if (configuration.isWithCoroutines())
                files.getAllWithoutLast().forEach { appendLine(it.toString()) }
            else files.forEach { appendLine(it.toString()) }
        }.toString()

    fun saveInOneFile(pathToSave: String) {
        val text = moveAllCodeInOneFile()
        File(pathToSave).writeText(text)
    }


    fun isBackendIgnores(backend: String): Boolean = configuration.ignoreBackends.contains(backend)

    fun getProjectSettingsAsCompilerArgs(backendType: String): CommonCompilerArguments {
        val args = when (backendType) {
            "JVM" -> K2JVMCompilerArguments()
            else -> K2JSCompilerArguments()
        }
        val languageDirective = "-XXLanguage:"
        val languageFeaturesAsArgs = configuration.languageSettings.joinToString(
            separator = " $languageDirective",
            prefix = languageDirective,
        ).split(" ")
        when (backendType) {
            "JVM" -> args.apply {
                K2JVMCompiler().parseArguments(
                    languageFeaturesAsArgs.toTypedArray(),
                    this as K2JVMCompilerArguments
                )
            }

            "JS" -> args.apply {
                K2JSCompiler().parseArguments(
                    languageFeaturesAsArgs.toTypedArray(),
                    this as K2JSCompilerArguments
                )
            }
        }
        args.optIn = configuration.useExperimental.toTypedArray()
        return args
    }


    fun copy(): Project {
        return Project(configuration, files.map { it.copy() }, language)
    }


    override fun toString(): String = files.joinToString("\n\n") {
        it.name + "\n" + it.text
    }
}