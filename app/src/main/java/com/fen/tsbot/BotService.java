package com.fen.tsbot;
import android.app.*;import android.content.Intent;import android.os.IBinder;import android.os.PowerManager;
import com.chaquo.python.PyObject;import com.chaquo.python.Python;import com.chaquo.python.android.AndroidPlatform;
import java.util.concurrent.ExecutorService;import java.util.concurrent.Executors;

public class BotService extends Service {
 public static final String START="com.fen.tsbot.START",STOP="com.fen.tsbot.STOP",RESULT="com.fen.tsbot.RESULT";
 private final ExecutorService worker=Executors.newSingleThreadExecutor();
 private PowerManager.WakeLock wakeLock;
 @Override public void onCreate(){super.onCreate();AssetInstaller.ensure(this);if(!Python.isStarted())Python.start(new AndroidPlatform(this));getSystemService(NotificationManager.class).createNotificationChannel(new NotificationChannel("bot","Bot đang chạy",NotificationManager.IMPORTANCE_LOW));PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);wakeLock=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"tsbot:BotService");wakeLock.setReferenceCounted(false);}
 private void keepCpuAwake(){if(wakeLock!=null&&!wakeLock.isHeld())wakeLock.acquire();}
 private void releaseCpu(){if(wakeLock!=null&&wakeLock.isHeld())wakeLock.release();}
 @Override public int onStartCommand(Intent intent,int flags,int startId){String action=intent==null?"":intent.getAction();if(intent==null||START.equals(action)){startForeground(7,notification(intent==null?"Bot đang chạy nền…":"Bot đang kết nối TS Online…"));keepCpuAwake();if(intent!=null){String payload=intent.getStringExtra("payload");int slot=intent.getIntExtra("slot",-1);String user=intent.getStringExtra("user");worker.execute(()->call("start_json",payload==null?"{}":payload,slot,user));}}else if(STOP.equals(action)){worker.execute(()->{call("stop_all",null,-1,null);releaseCpu();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();});}return START_STICKY;}
 private void call(String name,String arg,int slot,String user){String value;try{PyObject m=Python.getInstance().getModule("agent_bridge");value=arg==null?m.callAttr(name).toString():m.callAttr(name,arg).toString();}catch(Throwable t){value="{\"ok\":false,\"message\":\""+t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()).replace("\"","'")+"\"}";}Intent result=new Intent(RESULT).setPackage(getPackageName()).putExtra("json",value).putExtra("slot",slot);if(user!=null)result.putExtra("user",user);sendBroadcast(result);}
 private Notification notification(String text){PendingIntent pi=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);return new Notification.Builder(this,"bot").setSmallIcon(R.drawable.ic_launcher).setContentTitle("aTSBot Android").setContentText(text).setContentIntent(pi).setOngoing(true).build();}
 @Override public void onTaskRemoved(Intent rootIntent){super.onTaskRemoved(rootIntent);}
 @Override public IBinder onBind(Intent intent){return null;}@Override public void onDestroy(){releaseCpu();worker.shutdownNow();super.onDestroy();}
}
