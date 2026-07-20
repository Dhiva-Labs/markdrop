package com.example.md_converter_mobile

import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.concurrent.Executors
import android.os.Handler
import android.os.Looper

class MainActivity : FlutterActivity() {
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "md_engine")
            .setMethodCallHandler { call, result ->
                val method = call.method
                if (method != "convertFile" && method != "engineInfo") {
                    result.notImplemented()
                    return@setMethodCallHandler
                }
                val path = call.argument<String>("path")
                if (method == "convertFile" && path == null) {
                    result.error("bad_args", "path required", null)
                    return@setMethodCallHandler
                }
                executor.execute {
                    val json = try {
                        val module = Python.getInstance().getModule("convert")
                        if (method == "convertFile") {
                            module.callAttr("convert_file", path).toString()
                        } else {
                            module.callAttr("engine_info").toString()
                        }
                    } catch (e: Exception) {
                        "{\"ok\": false, \"error\": \"${e.message?.replace("\"", "'")?.take(300)}\"}"
                    }
                    mainHandler.post { result.success(json) }
                }
            }
    }
}
