package com.example.eclass;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.RetryPolicy;
import com.android.volley.toolbox.StringRequest;
import com.android.volley.toolbox.Volley;
import com.google.android.gms.common.ConnectionResult;
import com.google.android.gms.common.GoogleApiAvailability;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.messaging.FirebaseMessaging;

import org.jsoup.Connection;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutionException;

public class MainActivity extends AppCompatActivity {
    String studentInfo = "";
    String lessonsLinks = "";
    String lessonsNames = "";
    String deviceToken = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        getSupportActionBar().hide();
        TextView usernameField = findViewById(R.id.usernameField);
        TextView passwordField = findViewById(R.id.passwordField);
        Button loginBtn = findViewById(R.id.loginBtn);
        Button logoutBtn = findViewById(R.id.logoutBtn);
        Button readMeBtn = findViewById(R.id.readMeBtn);

        SharedPreferences sharedPreferences = getSharedPreferences("studentCredentials", MODE_PRIVATE);
        SharedPreferences.Editor editor = sharedPreferences.edit();
        String previousId = sharedPreferences.getString("id", null);

        if (previousId != null) {
            usernameField.setText(previousId);
            passwordField.setText(sharedPreferences.getString("password", null));
            logoutBtn.setVisibility(View.VISIBLE);
        }

        if (checkGooglePlayServicesAvailable()) {
            FirebaseMessaging.getInstance().getToken()
                    .addOnCompleteListener(new OnCompleteListener<String>() {
                        @Override
                        public void onComplete(@NonNull Task<String> task) {
                            if (!task.isSuccessful()) {
                                return;
                            }
                            // Get new FCM registration token
                            deviceToken = task.getResult();
                        }
                    });

            loginBtn.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    studentInfo = "";
                    lessonsLinks = "";
                    lessonsNames = "";
                    String currentId = usernameField.getText().toString();
                    String currentPassword = passwordField.getText().toString();
                    String messageToUser = "Unexpected error.";
                    String previousId = sharedPreferences.getString("id", null);

                    try {
                        ConnectivityManager manager = (ConnectivityManager) getApplicationContext().getSystemService(Context.CONNECTIVITY_SERVICE);
                        NetworkInfo activeNetwork = manager.getActiveNetworkInfo();
                        if (activeNetwork == null) {
                            messageToUser = "Internet connection error.";
                        }
                        else {
                            if ((!currentId.equals(previousId)) && (previousId != null)) {
                                messageToUser = "Please logout first from the previous account.";
                            }
                            else {
                                messageToUser = new Login().execute(currentId, currentPassword).get();
                                if (messageToUser.contains("be patient")) {
                                    postDataUsingVolley("http://192.168.2.105:9999/postUserData", editor, logoutBtn, usernameField, passwordField, currentId, currentPassword);
                                }
                            }
                        }
                    } catch (ExecutionException | InterruptedException e) {
                        e.printStackTrace();
                    }
                    showToast(messageToUser);
                }
            });

            logoutBtn.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    AlertDialog.Builder builder = new AlertDialog.Builder(view.getContext());
                    builder.setTitle("Confirm");
                    builder.setMessage("Are you sure you want to logout?");
                    builder.setCancelable(false);
                    builder.setPositiveButton("Yes", new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialogInterface, int i) {
                            String previousId = sharedPreferences.getString("id", null);
                            postDataUsingVolley("http://192.168.2.105:9999/deleteUserData", editor, logoutBtn, usernameField, passwordField, previousId, "");
                            dialogInterface.dismiss();
                        }
                    });
                    builder.setNegativeButton("Cancel", new DialogInterface.OnClickListener() {
                        @Override
                        public void onClick(DialogInterface dialogInterface, int i) {
                            dialogInterface.dismiss();
                        }
                    });
                    builder.show();
                }
            });
        }
        else {
            denyAccess();
        }
        readMeBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                DialogFragment dialogFragment = new DialogFragment();
                dialogFragment.show(getSupportFragmentManager(), "Read me fragment");
            }
        });
    }


    public class Login extends AsyncTask<String, String, String> {
        String response = "";
        @Override
        protected String doInBackground(String... params) {
            String homePageUrl = "https://eclass.uniwa.gr/";
            String userAgent = "python-requests/2.25.1";

            HashMap<String, String> getCookies = new HashMap<>();
            HashMap<String, String> postCookies = new HashMap<>();
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
                postCookies.putAll(postConn.cookies()); // save the cookies, this will be passed on to next request

                Document studentInfoDoc = Jsoup.connect("https://eclass.uniwa.gr/main/profile/display_profile.php")
                        .cookies(postCookies)
                        .get();

                studentInfo += params[0] + ", ";
                studentInfo += studentInfoDoc.select("div.profile-name").text() + ", ";
                studentInfo += deviceToken;

                Document lessonsDoc = Jsoup.connect("https://eclass.uniwa.gr/main/my_courses.php")
                        .cookies(postCookies)
                        .get();

                Elements linksElements = lessonsDoc.select("div.table-responsive").select("a[href]");
                for (Element linksElement : linksElements) {
                    String stringLessonLink = linksElement.attr("href");
                    if (stringLessonLink.contains("courses")) {
                        lessonsLinks += stringLessonLink + ", ";
                    }
                }
                if (!lessonsLinks.isEmpty()) {
                    lessonsLinks = lessonsLinks.substring(0, lessonsLinks.length() - 2);
                }

                Elements nameElements = lessonsDoc.select("div.table-responsive").select("a");
                for (Element nameElement : nameElements) {
                    if (!nameElement.text().equals("")) {
                        lessonsNames += nameElement.text() + ", ";
                    }
                }
                if (!lessonsNames.isEmpty()) {
                    lessonsNames = lessonsNames.substring(0, lessonsNames.length() - 2);
                }

                if (lessonsLinks.isEmpty()) {
                    response = "Due to security reasons please wait some seconds before you try a new login.";
                }
                else {
                    response = "Doing our stuff, please be patient... :)";
                }
            } catch (IOException e) {
                response = "Unexpected Error.";
            }
            return response;
        }
    }


    private void postDataUsingVolley(String url, SharedPreferences.Editor editor, Button logoutBtn, TextView usernameField, TextView passwordField, String id, String password) {
        StringRequest request = new StringRequest(Request.Method.POST, url,
                response -> {
                    if (response.equals("All ok.")) {
                        if (url.contains("postUserData")) {
                            manageCredentials(editor, id, password);
                            logoutBtn.setVisibility(View.VISIBLE);
                            hideKeyboard(getApplicationContext(), getCurrentFocus());
                            showToast("Welcome " + studentInfo.split(", ")[1] + "!");
                        } else {
                            editor.clear().apply();
                            usernameField.setText("cs");
                            passwordField.setText("");
                            logoutBtn.setVisibility(View.GONE);
                            showToast("You have successfully logged out.");
                        }
                    }
                },
                error -> showToast("Unexpected error. \nCan't communicate with the server.")) {

            @Override
            protected Map<String, String> getParams() {
                // below line we are creating a map for
                // storing our values in key and value pair.
                if (url.contains("deleteUserData")) {
                    studentInfo = id;
                    lessonsLinks = "delete";
                    lessonsNames = "delete";
                }
                Map<String, String> params = new HashMap<>();
                // on below line we are passing our key
                // and value pair to our parameters.
                params.put("studentInfo", studentInfo);
                params.put("lessonsLinks", lessonsLinks);
                params.put("lessonsNames", lessonsNames);

                // at last we are
                // returning our params.
                return params;
            }
        };
        // below line is to make
        // a json object request.
        request.setRetryPolicy(new DefaultRetryPolicy(600000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT));
        RequestQueue queue = Volley.newRequestQueue(MainActivity.this);
        queue.add(request);
    }


    private void denyAccess() {
        Button loginBtn = findViewById(R.id.loginBtn);
        loginBtn.setVisibility(View.GONE);
        TextView googlePlayServicesWarning = findViewById(R.id.googlePlayServicesWarning);
        googlePlayServicesWarning.setText("Sorry but the application can't use\n\"Push Notification\" service without \nGoogle Play Services installed on your device.");
    }


    private void manageCredentials(SharedPreferences.Editor editor, String id, String password) {
        editor.putString("id", id);
        editor.putString("password", password);
        editor.apply();
    }


    private boolean checkGooglePlayServicesAvailable() {
        final int status = GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(getApplicationContext());
        if (status == ConnectionResult.SUCCESS) {
            return true;
        }
        return false;
    }


    public void hideKeyboard(Context context, View view) {
        InputMethodManager inputMethodManager = (InputMethodManager) context.getSystemService(Activity.INPUT_METHOD_SERVICE);
        if (view != null) {
            inputMethodManager.hideSoftInputFromWindow(view.getWindowToken(), 0);
        }
    }


    private void showToast(String message) {
        Toast.makeText(getApplicationContext(), message, Toast.LENGTH_LONG).show();
    }
}
