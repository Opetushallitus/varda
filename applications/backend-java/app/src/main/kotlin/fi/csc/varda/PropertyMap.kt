package fi.csc.varda

import java.io.IOException
import java.util.*

/**
 * Helper class to provide environment properties for the application.
 */
object PropertyMap {
    private val properties = Properties()
    fun getProperty(key: String?): String {
        return properties.getProperty(key)
    }

    init {
        val resource = Thread.currentThread().contextClassLoader.getResourceAsStream("app.properties")
        try {
            properties.load(resource)
        } catch (e: IOException) {
            e.printStackTrace()
        }
    }
}
