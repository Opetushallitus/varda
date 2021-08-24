package fi.csc.varda

import io.ktor.server.engine.*
import io.ktor.server.netty.*

fun main() {
    embeddedServer(Netty, port = 8080) {
        configureRouting()
    }.start(wait = true)
}
