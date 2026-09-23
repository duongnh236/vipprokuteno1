package com.fen.tsbot;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;

/**
 * Splash hien thi luc mo app: logo + ten + SO PHIEN BAN (BuildConfig.VERSION_NAME).
 * version tu dong tang moi lan build (xem app/build.gradle task bumpVersion) -> splash luon
 * hien dung ban dang chay. Xong thi chuyen sang MainActivity.
 */
public class SplashActivity extends Activity {
    private static final long SPLASH_MS = 1400L;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable goMain = new Runnable() {
        @Override public void run() {
            if (isFinishing()) return;
            startActivity(new Intent(SplashActivity.this, MainActivity.class));
            finish();
        }
    };

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);
        TextView version = findViewById(R.id.splash_version);
        if (version != null) version.setText("Phiên bản " + BuildConfig.VERSION_NAME);
        handler.postDelayed(goMain, SPLASH_MS);
    }

    @Override protected void onDestroy() {
        handler.removeCallbacks(goMain);
        super.onDestroy();
    }
}
