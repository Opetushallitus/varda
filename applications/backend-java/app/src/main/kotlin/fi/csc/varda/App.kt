package fi.csc.varda


import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.calllogging.*
import org.slf4j.event.Level
import java.io.File
import java.io.FileInputStream
import java.security.KeyStore

fun main() {
    embeddedServer(Netty, configure = {
        val keystoreFile = File("/tmp/keystore.p12")

        // HTTPS connector on port 8080 (if TLS files exist)
        if (keystoreFile.exists()) {
            val keyStore = KeyStore.getInstance("PKCS12")
            FileInputStream(keystoreFile).use { fis ->
                keyStore.load(fis, "temppassword".toCharArray())
            }

            sslConnector(
                keyStore = keyStore,
                keyAlias = "tls",
                keyStorePassword = { "temppassword".toCharArray() },
                privateKeyPassword = { "temppassword".toCharArray() }
            ) {
                host = "0.0.0.0"
                port = 8080
            }
        } else {
            // HTTP connector on port 8080 (fallback if no TLS)
            connector {
                host = "0.0.0.0"
                port = 8080
            }
        }

        // Increase response timeout to 60 seconds as larger files are slower to encrypt with smaller Fargate vCPU
        // If a request fails with status 502 and there are no error logs, it may be because of a timeout
        requestReadTimeoutSeconds = 60
    }) {
        module()
    }.start(wait = true)
}

fun Application.module() {
    install(CallLogging) {
        level = Level.INFO
        // Disable colours as Logback JSON layout escapes them
        disableDefaultColors()
    }

    configureRouting()
}
