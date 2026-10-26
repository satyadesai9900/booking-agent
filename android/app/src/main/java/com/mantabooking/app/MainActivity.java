package com.mantabooking.app;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.browser.customtabs.CustomTabsIntent;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private SwipeRefreshLayout swipeRefreshLayout;
    private ValueCallback<Uri[]> fileUploadCallback;
    private final static int FILE_CHOOSER_REQUEST_CODE = 1001;

    // Production URL (Change to your live cloud deployment domain)
    // For local Android Emulator development, you can use "http://10.0.2.2:5000"
    private static final String APP_URL = "https://mantabooking.onrender.com";
    private static final String DEV_URL = "http://10.0.2.2:5000";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Dynamic layout setup
        swipeRefreshLayout = new SwipeRefreshLayout(this);
        webView = new WebView(this);
        swipeRefreshLayout.addView(webView);
        setContentView(swipeRefreshLayout);

        // Configure Swipe to Refresh
        swipeRefreshLayout.setColorSchemeColors(0xFF6366F1, 0xFF4F46E5);
        swipeRefreshLayout.setOnRefreshListener(() -> webView.reload());

        // Configure WebView Settings
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        
        // Append MantaBooking Android client tag
        String customUA = settings.getUserAgentString() + " MantaBookingAndroid/1.0";
        settings.setUserAgentString(customUA);

        // Custom WebViewClient to route internal vs external carrier links
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();

                // If URL is an external carrier booking site, open via Chrome Custom Tabs
                if (isExternalCarrierPlatform(url)) {
                    openInCustomTab(url);
                    return true;
                }

                // If deep link or mailto
                if (url.startsWith("mailto:") || url.startsWith("tel:")) {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                }

                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                swipeRefreshLayout.setRefreshing(false);
            }
        });

        // WebChromeClient for File Choosing and Loading
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {
                if (fileUploadCallback != null) {
                    fileUploadCallback.onReceiveValue(null);
                }
                fileUploadCallback = filePathCallback;

                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST_CODE);
                } catch (Exception e) {
                    fileUploadCallback = null;
                    return false;
                }
                return true;
            }
        });

        // Handle Back button
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });

        // Determine URL to load (check if debug or production)
        String targetUrl = BuildConfig.DEBUG ? DEV_URL : APP_URL;
        webView.loadUrl(targetUrl);
    }

    private boolean isExternalCarrierPlatform(String url) {
        String lower = url.toLowerCase();
        return lower.contains("irctc.co.in") ||
               lower.contains("confirmtkt.com") ||
               lower.contains("railyatri.in") ||
               lower.contains("google.com/travel/flights") ||
               lower.contains("skyscanner.com") ||
               lower.contains("makemytrip.com") ||
               lower.contains("bookmyshow.com") ||
               lower.contains("redbus.in") ||
               lower.contains("booking.com") ||
               lower.contains("checkmytrip.com") ||
               lower.contains("abhibus.com");
    }

    private void openInCustomTab(String url) {
        try {
            CustomTabsIntent customTabsIntent = new CustomTabsIntent.Builder()
                    .setShowTitle(true)
                    .build();
            customTabsIntent.launchUrl(this, Uri.parse(url));
        } catch (Exception e) {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            startActivity(intent);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (fileUploadCallback != null) {
                Uri[] results = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
                fileUploadCallback.onReceiveValue(results);
                fileUploadCallback = null;
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }
}
