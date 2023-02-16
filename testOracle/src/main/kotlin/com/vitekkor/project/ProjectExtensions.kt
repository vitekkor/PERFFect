package com.vitekkor.project

fun <T> Iterable<T>.getAllWithout(el: T): List<T> {
    val list: ArrayList<T> = arrayListOf()
    for (item in this) {
        if (item != el) list.add(item)
    }
    return list
}

fun <T> Iterable<T>.getAllWithout(index: Int): List<T> {
    val list: java.util.ArrayList<T> = arrayListOf()
    for ((count, item) in withIndex()) {
        if (count != index) list.add(item)
    }
    return list
}

fun <T> Iterable<T>.getAllWithoutLast(): List<T> {
    var size = 0
    for (e in this.iterator()) size++
    return getAllWithout(size - 1)
}
