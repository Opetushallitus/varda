package fi.csc.varda

import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.callloging.*
import org.slf4j.event.Level

fun main() {
    embeddedServer(Netty, port = 8080, configure = {
        // Increase response timeout to 60 seconds as larger files are slower to encrypt with smaller Fargate vCPU
        // If a request fails with status 502 and there are no error logs, it may be because of a timeout
        // https://ktor.io/docs/engines.html#netty-code
        // https://api.ktor.io/ktor-server/ktor-server-netty/io.ktor.server.netty/-netty-application-engine/-configuration/index.html
        responseWriteTimeoutSeconds = 60
    }) {
        install(CallLogging) {
            level = Level.INFO
            // Disable colours as Logback JSON layout escapes them
            disableDefaultColors()
        }
        configureRouting()
    }.start(wait = true)
}
