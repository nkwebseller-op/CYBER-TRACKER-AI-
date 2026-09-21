package com.cyberai.shell

import android.annotation.SuppressLint
import android.net.Uri
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature

/**
 * A locked-down WebView shell that loads the Cyber AI dashboard.
 *
 * Deliberately narrow:
 *  - File-access APIs on the WebView are all disabled (no local file
 *    schemes, no content URIs).
 *  - JavaScript is enabled because the dashboard is a Next.js app;
 *    there is no `addJavascriptInterface` bridge, so the page cannot
 *    reach native Android APIs.
 *  - Any URL that isn't on the configured dashboard host opens in the
 *    system browser instead of taking over this WebView.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setTheme(R.style.Theme_CyberAIShell)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.web_view)
        val dashboardUrl = BuildConfig.DASHBOARD_URL
        val dashboardHost = Uri.parse(dashboardUrl).host ?: ""

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mediaPlaybackRequiresUserGesture = true
            cacheMode = WebSettings.LOAD_DEFAULT
            userAgentString = "$userAgentString CyberAIShell/0.1.0"
        }

        // Match the dashboard's dark theme.
        if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
            WebSettingsCompat.setAlgorithmicDarkeningAllowed(webView.settings, true)
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView, request: WebResourceRequest
            ): Boolean {
                val url = request.url
                if (url.host == dashboardHost) {
                    return false // let the WebView load it
                }
                // Off-host link -> hand off to the system browser
                val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, url)
                startActivity(intent)
                return true
            }
        }

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            webView.loadUrl(dashboardUrl)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
