package fi.csc.varda

import io.ktor.http.*
import io.ktor.http.content.*
import io.ktor.server.application.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import java.io.*

fun Application.configureRouting() {
    routing {
        get("/") {
            call.respondText("Hello, world!")
        }
        get("/ping/") {
            call.respondText("Pong!")
        }
        post("/upload") {
            var password = ""
            var filename = ""
            var inputStream = ByteArrayInputStream.nullInputStream()

            val multipartData = call.receiveMultipart()
            multipartData.forEachPart { part ->
                when (part) {
                    is PartData.FormItem -> {
                        if (part.name.equals("password")) {
                            password = part.value
                        }
                    }
                    is PartData.FileItem -> {
                        filename = part.originalFileName as String
                        inputStream = part.streamProvider()
                    }
                    else -> { }
                }
            }

            call.response.header(
                HttpHeaders.ContentDisposition,
                ContentDisposition.Attachment.withParameter(ContentDisposition.Parameters.FileName, filename)
                    .toString()
            )
            call.respondOutputStream(ContentType.defaultForFileExtension("xlsx"), HttpStatusCode.OK) {
                ExcelEncrypt.encrypt(password, inputStream, this)
            }
        }
    }
}
