package fi.csc.varda

import ch.qos.logback.contrib.jackson.JacksonJsonFormatter

class CustomJsonLogFormatter : JacksonJsonFormatter() {
    override fun toJsonString(m: MutableMap<Any?, Any?>): String {
        // Rename thread field in logs so that it does not clash with existing field in OpenSearch
        // Fargate -> OpenSearch transfer fails if fields send data with different types
        m["threadJava"] = m["thread"]
        m.remove("thread")
        m["source"] = "java"
        return super.toJsonString(m)
    }
}
