package com.example.md_converter_mobile

import android.content.ContentValues
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.provider.OpenableColumns
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var channel: MethodChannel? = null
    private val pendingShares = mutableListOf<Map<String, String>>()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "md_engine")
        channel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                "convertFile", "convertUrl", "engineInfo", "probeImports" -> runPython(call.method, call.argument("arg"), result)
                "getPendingShares" -> {
                    result.success(ArrayList(pendingShares))
                    pendingShares.clear()
                }
                "saveToDownloads" -> {
                    val name = call.argument<String>("name") ?: "converted.md"
                    val content = call.argument<String>("content") ?: ""
                    try {
                        result.success(saveToDownloads(name, content))
                    } catch (e: Exception) {
                        result.error("save_failed", e.message, null)
                    }
                }
                else -> result.notImplemented()
            }
        }
        handleIntent(intent, initial = true)
    }

    private fun runPython(method: String, arg: String?, result: MethodChannel.Result) {
        executor.execute {
            val json = try {
                val module = Python.getInstance().getModule("convert")
                when (method) {
                    "convertFile" -> module.callAttr("convert_file", arg).toString()
                    "convertUrl" -> module.callAttr("convert_url", arg).toString()
                    "probeImports" -> module.callAttr("probe_imports").toString()
                    else -> module.callAttr("engine_info").toString()
                }
            } catch (e: Exception) {
                "{\"ok\": false, \"error\": \"${e.message?.replace("\"", "'")?.take(300)}\"}"
            }
            mainHandler.post { result.success(json) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent, initial = false)
    }

    private fun handleIntent(intent: Intent?, initial: Boolean) {
        if (intent == null) return
        val shares = mutableListOf<Map<String, String>>()
        when (intent.action) {
            Intent.ACTION_SEND -> {
                val text = intent.getStringExtra(Intent.EXTRA_TEXT)
                @Suppress("DEPRECATION")
                val uri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM)
                if (uri != null) {
                    copyToCache(uri)?.let { shares.add(mapOf("type" to "file", "value" to it)) }
                } else if (!text.isNullOrBlank()) {
                    shares.add(mapOf("type" to "text", "value" to text))
                }
            }
            Intent.ACTION_SEND_MULTIPLE -> {
                @Suppress("DEPRECATION")
                intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)?.forEach { uri ->
                    copyToCache(uri)?.let { shares.add(mapOf("type" to "file", "value" to it)) }
                }
            }
        }
        if (shares.isEmpty()) return
        // Deliver live if Flutter is up; otherwise queue for getPendingShares.
        val ch = channel
        if (!initial && ch != null) {
            mainHandler.post { ch.invokeMethod("onShared", shares) }
        } else {
            pendingShares.addAll(shares)
        }
    }

    private fun copyToCache(uri: Uri): String? {
        return try {
            var name = "shared-${System.currentTimeMillis()}"
            contentResolver.query(uri, null, null, null, null)?.use { c ->
                val ix = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (ix >= 0 && c.moveToFirst()) c.getString(ix)?.let { name = it }
            }
            val dest = File(File(cacheDir, "shared").apply { mkdirs() }, name)
            contentResolver.openInputStream(uri)?.use { input ->
                dest.outputStream().use { input.copyTo(it) }
            } ?: return null
            dest.absolutePath
        } catch (e: Exception) {
            null
        }
    }

    private fun saveToDownloads(name: String, content: String): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, "text/markdown")
                put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Markdrop")
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: throw IllegalStateException("MediaStore insert failed")
            contentResolver.openOutputStream(uri)?.use { it.write(content.toByteArray()) }
            return "Downloads/Markdrop/$name"
        } else {
            @Suppress("DEPRECATION")
            val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "Markdrop")
            dir.mkdirs()
            val f = File(dir, name)
            f.writeText(content)
            return f.absolutePath
        }
    }
}
