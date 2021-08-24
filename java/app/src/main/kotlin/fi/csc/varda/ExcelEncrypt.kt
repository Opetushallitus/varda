package fi.csc.varda

import org.apache.poi.openxml4j.exceptions.InvalidFormatException
import org.apache.poi.openxml4j.opc.OPCPackage
import org.apache.poi.poifs.crypt.EncryptionInfo
import org.apache.poi.poifs.crypt.EncryptionMode
import org.apache.poi.poifs.crypt.Encryptor
import org.apache.poi.poifs.filesystem.POIFSFileSystem
import java.io.*
import java.security.GeneralSecurityException

object ExcelEncrypt {
    /**
     * https://poi.apache.org/encryption.html
     */
    fun encrypt(password: String, inputStream: InputStream, outputStream: OutputStream) {
        try {
            POIFSFileSystem().use { fs ->
                val info = EncryptionInfo(EncryptionMode.agile)
                val enc: Encryptor = info.encryptor
                enc.confirmPassword(password)

                OPCPackage.open(inputStream).use { opc ->
                    enc.getDataStream(fs).use { os ->
                        opc.save(os)
                    }
                }
                outputStream.use { fos -> fs.writeFilesystem(fos) }
            }
        } catch (e: IOException) {
            e.printStackTrace()
        } catch (e: InvalidFormatException) {
            e.printStackTrace()
        } catch (e: GeneralSecurityException) {
            e.printStackTrace()
        }
    }
}
