package com.vitekkor.perffect.project

fun <T> Iterable<T>.getAllWithout(el: T): List<T> {
    val list: ArrayList<T> = arrayListOf()
    for (item in this) {
        if (item != el) list.add(item)
    }
    return list
}
