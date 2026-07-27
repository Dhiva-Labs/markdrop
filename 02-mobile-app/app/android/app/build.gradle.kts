plugins {
    id("com.android.application")
    id("com.chaquo.python")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.md_converter_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.example.md_converter_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = maxOf(24, flutter.minSdkVersion)  // Chaquopy Python 3.12 needs 24+
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        ndk {
            // Replace, don't append: Flutter pre-seeds armeabi-v7a, which has
            // no Chaquopy Python 3.12 build.
            abiFilters.clear()
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
            // R8 trips over ML Kit's generated rules; the APK is dominated by
            // the bundled Python anyway, so shrinking buys little.
            isMinifyEnabled = false
            isShrinkResources = false
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

chaquopy {
    defaultConfig {
        version = "3.12"  // markitdown needs >=3.10; Chaquopy defaults lower
        buildPython("/home/dhivakar/dhiva-labs/md-files-dhivalabs/02-mobile-app/.buildpython/bin/python")
        pip {
            // markitdown without magika (needs onnxruntime, unavailable on
            // Android) — deps listed manually, magika stubbed in src/main/python.
            options("--no-deps")
            install("markitdown==0.1.6")
            // core deps (minus magika)
            install("beautifulsoup4==4.13.4")
            install("soupsieve==2.7")
            install("requests==2.32.4")
            install("urllib3==2.5.0")
            install("idna==3.10")
            install("certifi==2025.6.15")
            install("charset-normalizer==3.4.2")
            install("markdownify==0.13.1")
            install("six==1.17.0")
            install("defusedxml==0.7.1")
            // docx
            install("mammoth==1.11.0")
            install("cobble==0.1.4")
            // lxml + Pillow load on 4KB-page devices (most phones today);
            // on 16KB-page devices they fail to dlopen and pptx degrades
            // cleanly (docx/pdf/html/etc all still work — see README)
            install("lxml==5.3.0")
            install("chaquopy-libxml2")
            install("chaquopy-libxslt")
            install("Pillow==11.0.0")
            install("chaquopy-libjpeg")
            install("chaquopy-libpng")
            // pptx
            install("python-pptx==1.0.2")
            install("XlsxWriter==3.2.9")
            install("typing-extensions==4.16.0")
            // xlsx (openpyxl instead of pandas — keeps the APK sane)
            install("openpyxl==3.1.5")
            install("et-xmlfile==2.0.0")
            // pdf (text extraction; pdfplumber/table support evaluated later)
            install("pdfminer.six==20250506")
            // youtube transcripts (pure python)
            install("youtube-transcript-api==1.2.4")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir("src/main/python")
        }
    }
}
