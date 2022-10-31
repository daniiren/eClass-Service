package com.example.eclass;

import androidx.appcompat.app.AppCompatActivity;

import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.jsoup.Connection;
import org.jsoup.Jsoup;

import java.io.IOException;
import java.util.HashMap;
import java.util.concurrent.ExecutionException;

public class GoToBrowser extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_go_to_browser);

        SharedPreferences sharedPreferences = getSharedPreferences("studentCredentials", MODE_PRIVATE);
        String username = sharedPreferences.getString("id", null);
        String password = sharedPreferences.getString("password", null);
        String url = "https://eclass.uniwa.gr/main/my_courses.php";
        String cookie = "";

        try {
            Login login = new Login();
            cookie = login.execute(username, password).get();
            String[] splittedCookie = cookie.split("=");
            cookie = splittedCookie[1].substring(0, splittedCookie[1].length() - 1);
            System.out.println(cookie);
        } catch (ExecutionException e) {
            e.printStackTrace();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        WebView webView = (WebView) findViewById(R.id.webView);
        webView.setWebViewClient(new WebViewClient());  // For letting us to navigate to eclass on our webview with the specific cookies
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        CookieManager.getInstance().setCookie(url, "PHPSESSID=" + cookie + "; path=/");
        webView.loadUrl(url);
    }

    public class Login extends AsyncTask<String, String, String> {
        String cookies = "";
        @Override
        protected String doInBackground(String... params) {
            String homePageUrl = "https://eclass.uniwa.gr/";
            String userAgent = "python-requests/2.25.1";

            HashMap<String, String> getCookies = new HashMap<>();
            HashMap<String, String> postFormData = new HashMap<>();

            try {
                Connection.Response getConn = Jsoup.connect(homePageUrl).method(Connection.Method.GET).userAgent(userAgent).execute();
                getCookies.putAll(getConn.cookies()); // save the cookies, this will be passed on to next request

                postFormData.put("uname", params[0]);
                postFormData.put("pass", params[1]);
                postFormData.put("submit", "Είσοδος");
                Connection.Response postConn = Jsoup.connect(homePageUrl)
                        .cookies(getCookies)
                        .data(postFormData)
                        .method(Connection.Method.POST)
                        .userAgent(userAgent)
                        .header("Accept-Encoding", "gzip, deflate")
                        .header("Accept", "*/*")
                        .header("Connection", "keep-alive")
                        .execute();

                cookies = String.valueOf(postConn.cookies());
            } catch (IOException e) {
                e.printStackTrace();
            }
            return cookies;
        }
    }
}