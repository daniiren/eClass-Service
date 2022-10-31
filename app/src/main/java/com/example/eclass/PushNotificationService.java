package com.example.eclass;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationManagerCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

import java.util.Random;

public class PushNotificationService extends FirebaseMessagingService {
    @Override
    public void onMessageReceived(@NonNull RemoteMessage remoteMessage) {
        String title = remoteMessage.getData().get("title");
        String body = remoteMessage.getData().get("body");
        int randomId = new Random().nextInt(1000);
        final String CHANNEL_ID = "channelIdHere";

        NotificationChannel notificationChannel = new NotificationChannel(
                CHANNEL_ID,
                "channelName",
                NotificationManager.IMPORTANCE_HIGH
        );

        Intent goToBrowserIntent = new Intent(PushNotificationService.this, GoToBrowser.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, goToBrowserIntent, PendingIntent.FLAG_UPDATE_CURRENT);

        getSystemService(NotificationManager.class).createNotificationChannel(notificationChannel);
        Notification.Builder notification = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(body)
                .setContentIntent(pendingIntent)
                .setStyle(new Notification.BigTextStyle().bigText(body))
                .setSmallIcon(R.drawable.ic_launcher_background)
                .setAutoCancel(true);

        NotificationManagerCompat.from(PushNotificationService.this).notify(randomId, notification.build());
        super.onMessageReceived(remoteMessage);
    }
}
