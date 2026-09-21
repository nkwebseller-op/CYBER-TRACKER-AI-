plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.cyberai.shell"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.cyberai.shell"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        // Injected from GitHub Actions or local gradle.properties.
        // Falls back to a placeholder that shows a helpful onboarding
        // screen instead of a broken WebView.
        val dashboardUrl = (project.findProperty("cyberaiDashboardUrl") as? String)
            ?: System.getenv("CYBERAI_DASHBOARD_URL")
            ?: "https://cyberai.local/onboarding"
        buildConfigField("String", "DASHBOARD_URL", "\"$dashboardUrl\"")
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("debug")
        }
        debug {
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.webkit:webkit:1.11.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
}
