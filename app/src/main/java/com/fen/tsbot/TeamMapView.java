package com.fen.tsbot;

import android.content.Context;
import android.graphics.*;
import android.view.View;
import android.view.MotionEvent;
import org.json.*;
import java.util.*;
import android.util.Base64;

/**
 * Ban do team live.
 *
 * Chia 2 LOP de do lag khi cap nhat toa do:
 *   - LOP TINH (nen + luoi + dia hinh + SAFE + dich + tieu de/chu thich) ve 1 LAN vao `staticBmp`,
 *     chi ve lai khi doi map/doi vung nhin/doi kich thuoc/co dia hinh moi. "Vao map ve 1 lan".
 *   - LOP DONG (nguoi choi/quai/member/route/dau cham) ve moi frame, re va da cull ngoai khung.
 * Vi tri dong duoc NOI SUY (lerp) giua 2 snapshot (poll 1 giay) nen di chuyen muot, khong nhay cuc.
 */
public class TeamMapView extends View {
    private JSONObject snapshot = new JSONObject();
    private int terrainMap=-1;private byte[] terrainData=new byte[0];
    private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint bmpPaint = new Paint();   // paint rieng cho bitmap (khong dinh alpha cua text/tag)
    private final int bg=Color.rgb(7,16,29), grid=Color.rgb(27,49,72), gold=Color.rgb(229,184,83);
    private double loX,hiX,loY,hiY; private float plotLeft,plotRight,plotTop,plotBottom; private boolean hasBounds=false;
    private double tapX,tapY; private boolean hasTap=false; private JSONArray route=new JSONArray(); private OnMapTapListener tapListener;
    private android.graphics.Bitmap staticBmp; private String staticKey="";

    // Noi suy vi tri giua 2 snapshot. ANIM_MS ~ bang chu ky poll 1s de chuyen dong lien tuc.
    private static final long ANIM_MS=900L;
    private long animStart=0L; private boolean animating=false;
    private final Map<Long,float[]> entAnim=new HashMap<>();    // entity id -> [prevX,prevY,targetX,targetY]
    private final Map<String,float[]> teamAnim=new HashMap<>(); // user      -> [prevX,prevY,targetX,targetY]
    private final Runnable animTick=new Runnable(){public void run(){if(!animating)return;if(!isShown()){animating=false;return;}invalidate();if(System.currentTimeMillis()-animStart<ANIM_MS)postOnAnimation(this);else animating=false;}};
    public interface OnMapTapListener{void onMapTap(int x,int y);}

    public TeamMapView(Context c){super(c);p.setTypeface(Typeface.create(Typeface.MONOSPACE,Typeface.NORMAL));setBackgroundColor(bg);}
    public void setOnMapTapListener(OnMapTapListener listener){tapListener=listener;}

    public synchronized void setSnapshot(JSONObject value){
        JSONObject next=value==null?new JSONObject():value;
        boolean mapChanged=next.optInt("map")!=snapshot.optInt("map")||next.optInt("channel")!=snapshot.optInt("channel");
        if(mapChanged){hasBounds=false;hasTap=false;route=new JSONArray();entAnim.clear();teamAnim.clear();staticBmp=null;}
        snapshot=next;
        int map=next.optInt("map");
        if(terrainMap!=map||terrainData.length==0){JSONObject terrain=next.optJSONObject("collision");try{terrainData=terrain==null?new byte[0]:Base64.decode(terrain.optString("data",""),Base64.DEFAULT);}catch(Exception e){terrainData=new byte[0];}terrainMap=map;}
        updateAnimTargets(next);
        invalidate();
    }
    public synchronized void setRoute(JSONArray value,JSONArray actualTarget){route=value==null?new JSONArray():value;if(actualTarget!=null){tapX=actualTarget.optDouble(0);tapY=actualTarget.optDouble(1);hasTap=true;}invalidate();}

    // UI bao con thieu luoi va cham cua map hien tai -> nho bridge gui lai chuoi base64 nang.
    public synchronized boolean needsTerrain(){return terrainData==null||terrainData.length==0;}

    private static float ease(float t){return t*t*(3f-2f*t);}

    // Chuyen vi tri hien tai (dang noi suy) thanh `prev`, roi nhan toa do moi lam `target` -> muot.
    // Tra ve True neu co thay doi thuc su (moi chay vong lap ve lai; dung yen thi khong ton pin).
    private boolean updateAnimTargets(JSONObject next){
        long now=System.currentTimeMillis();
        float t=animating?ease(Math.min(1f,(now-animStart)/(float)ANIM_MS)):1f;
        boolean firstFill=entAnim.isEmpty()&&teamAnim.isEmpty();
        boolean changed=false;
        JSONArray ents=next.optJSONArray("entities");
        Set<Long> seenE=new HashSet<>();
        if(ents!=null)for(int i=0;i<ents.length();i++){
            JSONObject e=ents.optJSONObject(i);if(e==null)continue;
            long id=e.optLong("id",-1);double x=e.optDouble("x"),y=e.optDouble("y");
            if(id<0||x<=0||y<=0)continue;
            float[] a=entAnim.get(id);
            if(a==null){entAnim.put(id,new float[]{(float)x,(float)y,(float)x,(float)y});changed=true;}
            else{if(Math.abs(a[2]-x)>0.5f||Math.abs(a[3]-y)>0.5f)changed=true;a[0]=a[0]+(a[2]-a[0])*t;a[1]=a[1]+(a[3]-a[1])*t;a[2]=(float)x;a[3]=(float)y;}
            seenE.add(id);
        }
        int before=entAnim.size();entAnim.keySet().retainAll(seenE);if(entAnim.size()!=before)changed=true;
        JSONArray team=next.optJSONArray("team");
        Set<String> seenT=new HashSet<>();
        if(team!=null)for(int i=0;i<team.length();i++){
            JSONObject m=team.optJSONObject(i);if(m==null)continue;
            String u=m.optString("user");double x=m.optDouble("x"),y=m.optDouble("y");
            if(u.isEmpty()||x<=0||y<=0)continue;
            float[] a=teamAnim.get(u);
            if(a==null){teamAnim.put(u,new float[]{(float)x,(float)y,(float)x,(float)y});changed=true;}
            else{if(Math.abs(a[2]-x)>0.5f||Math.abs(a[3]-y)>0.5f)changed=true;a[0]=a[0]+(a[2]-a[0])*t;a[1]=a[1]+(a[3]-a[1])*t;a[2]=(float)x;a[3]=(float)y;}
            seenT.add(u);
        }
        before=teamAnim.size();teamAnim.keySet().retainAll(seenT);if(teamAnim.size()!=before)changed=true;
        if(firstFill)return false;
        if(changed){animStart=now;if(!animating){animating=true;postOnAnimation(animTick);}}
        return changed;
    }

    private void text(Canvas c,String s,float x,float y,float size,int color){p.setStyle(Paint.Style.FILL);p.setTextSize(size);p.setColor(color);c.drawText(s,x,y,p);}
    private void tag(Canvas c,String s,float x,float y,float size,int color){p.setTextSize(size);p.setStyle(Paint.Style.FILL);float width=p.measureText(s);p.setColor(Color.argb(205,5,12,22));c.drawRoundRect(x-4,y-size-3,x+width+4,y+5,5,5,p);text(c,s,x,y,size,color);}
    private void dot(Canvas c,float x,float y,float radius,int color){p.setStyle(Paint.Style.FILL);p.setColor(color);c.drawCircle(x,y,radius,p);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2);p.setColor(Color.WHITE);c.drawCircle(x,y,radius,p);}
    private boolean blocked(byte[] data,int gh,int x,int y){if(x<0||y<0||x*gh+y>=data.length)return true;int v=data[x*gh+y]&255;return (v&1)!=0||(v&4)!=0;}

    private PointF prj(double x,double y){return new PointF((float)(plotLeft+(x-loX)/(hiX-loX)*(plotRight-plotLeft)),(float)(plotTop+(y-loY)/(hiY-loY)*(plotBottom-plotTop)));}

    // Ve luoi va cham + luoi o vao bitmap TINH (chi 1 lan cho moi vung nhin).
    private void renderTerrain(Canvas c,JSONObject collision){
        if(collision==null||collision.optInt("grid_w")<=0)return;
        try{
            int gw=collision.getInt("grid_w"),gh=collision.getInt("grid_h"),ox=collision.getInt("origin_x"),oy=collision.getInt("origin_y"),cell=collision.optInt("cell",20);
            byte[] data=terrainData;if(data.length<gw*gh)return;
            c.save();c.clipRect(plotLeft,plotTop,plotRight,plotBottom);
            int gx0=Math.max(0,(int)Math.floor((loX-ox)/cell)),gx1=Math.min(gw-1,(int)Math.ceil((hiX-ox)/cell));
            int gy0=Math.max(0,(int)Math.floor((loY-oy)/cell)),gy1=Math.min(gh-1,(int)Math.ceil((hiY-oy)/cell));
            for(int gx=gx0;gx<=gx1;gx++){double x0=ox+gx*cell,x1=x0+cell;
                for(int gy=gy0;gy<=gy1;gy++){double y0=oy+gy*cell,y1=y0+cell;
                    int v=data[gx*gh+gy]&255;boolean wall=(v&1)!=0||(v&4)!=0,sea=(v&2)!=0;
                    PointF a=prj(x0,y0),b=prj(x1,y1);
                    p.setStyle(Paint.Style.FILL);p.setColor(wall?Color.argb(155,90,28,35):(sea?Color.argb(105,25,82,125):Color.argb(35,70,145,105)));c.drawRect(a.x,a.y,b.x,b.y,p);
                    if(wall){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.5f);p.setColor(Color.rgb(225,75,75));
                        if(!blocked(data,gh,gx-1,gy))c.drawLine(a.x,a.y,a.x,b.y,p);
                        if(!blocked(data,gh,gx+1,gy))c.drawLine(b.x,a.y,b.x,b.y,p);
                        if(!blocked(data,gh,gx,gy-1))c.drawLine(a.x,a.y,b.x,a.y,p);
                        if(!blocked(data,gh,gx,gy+1))c.drawLine(a.x,b.y,b.x,b.y,p);}
                }}
            c.restore();
        }catch(Exception ignored){}
    }

    private void drawGrid(Canvas c){p.setStrokeWidth(1);p.setColor(grid);for(int i=0;i<=8;i++){float x=plotLeft+(plotRight-plotLeft)*i/8f,y=plotTop+(plotBottom-plotTop)*i/8f;c.drawLine(x,plotTop,x,plotBottom,p);c.drawLine(plotLeft,y,plotRight,y,p);}}
    private void drawSafe(Canvas c,JSONArray safe){if(safe==null)return;for(int i=0;i<safe.length();i++){JSONArray q=safe.optJSONArray(i);if(q==null)continue;PointF a=prj(q.optDouble(0),q.optDouble(1));p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);p.setColor(Color.rgb(65,170,120));c.drawCircle(a.x,a.y,10,p);text(c,"SAFE",a.x+12,a.y,10,Color.rgb(100,220,160));}}
    private void drawTarget(Canvas c,JSONArray t){if(t==null)return;PointF a=prj(t.optDouble(0),t.optDouble(1));p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);p.setColor(Color.RED);c.drawLine(a.x-9,a.y-9,a.x+9,a.y+9,p);c.drawLine(a.x+9,a.y-9,a.x-9,a.y+9,p);text(c,"BÃI TRAIN",a.x+12,a.y,11,Color.rgb(255,120,100));}
    private String arrKey(JSONArray a){if(a==null)return "";StringBuilder sb=new StringBuilder();for(int i=0;i<a.length();i++){JSONArray q=a.optJSONArray(i);if(q==null)continue;sb.append((int)q.optDouble(0)).append(',').append((int)q.optDouble(1)).append(';');}return sb.toString();}

    // Ve LOP TINH vao bitmap cache. Key gom map/kenh/vung nhin/kich thuoc/dia hinh/safe/dich.
    private void drawStatic(Canvas c,float w,float h,int map,int channel,String place,JSONArray safe){
        JSONArray target=snapshot.optJSONArray("target");
        String key=map+":"+channel+":"+place+":"+loX+":"+hiX+":"+loY+":"+hiY+":"+(int)w+":"+(int)h+":"+terrainMap+":"+System.identityHashCode(terrainData)+":"+arrKey(safe)+":"+(target==null?"":((int)target.optDouble(0))+","+((int)target.optDouble(1)));
        if(staticBmp==null||staticBmp.getWidth()!=(int)w||staticBmp.getHeight()!=(int)h||!key.equals(staticKey)){
            if(staticBmp==null||staticBmp.getWidth()!=(int)w||staticBmp.getHeight()!=(int)h)staticBmp=Bitmap.createBitmap((int)w,(int)h,Bitmap.Config.ARGB_8888);
            Canvas bc=new Canvas(staticBmp);
            bc.drawColor(bg);
            drawGrid(bc);
            renderTerrain(bc,snapshot.optJSONObject("collision"));
            drawSafe(bc,safe);
            drawTarget(bc,target);
            text(bc,"🗺  "+place+"  •  Phân khu "+channel,18,30,16,gold);
            text(bc,"● Leader  ● Quân sư  ● Member  ● Người chơi  ● Quái  ■ Tường/Nước",18,h-58,11,Color.LTGRAY);
            text(bc,"Chạm bản đồ: leader kéo nguyên PT • cập nhật 1 giây",18,h-30,11,Color.rgb(130,160,190));
            staticKey=key;
        }
        c.drawBitmap(staticBmp,0,0,bmpPaint);
    }

    // Tim diem neo camera: uu tien account dang focus, fallback member dau tien cung map/kenh.
    private double[] findAnchor(JSONArray team,int map,int channel){
        if(team==null)return null;
        String focus=snapshot.optString("focus_user");
        double[] first=null,focusPt=null;
        for(int i=0;i<team.length();i++){JSONObject x=team.optJSONObject(i);if(x==null)continue;if(x.optInt("map")!=map||x.optInt("channel")!=channel||x.optInt("x")<=0)continue;double[] pt={x.optDouble("x"),x.optDouble("y")};if(first==null)first=pt;if(focusPt==null&&x.optString("user").equals(focus))focusPt=pt;}
        return focusPt!=null?focusPt:first;
    }

    // Camera: vao map chot 1 lan; sau do CHI doi khi diem neo toi gan bien (hiem) -> han che ve lai map.
    private void updateCamera(double[] anchor){
        if(!hasBounds){loX=anchor[0]-800;hiX=anchor[0]+800;loY=anchor[1]-800;hiY=anchor[1]+800;hasBounds=true;return;}
        double cx=(loX+hiX)/2,cy=(loY+hiY)/2;
        if(Math.abs(anchor[0]-cx)>640||Math.abs(anchor[1]-cy)>640){loX=anchor[0]-800;hiX=anchor[0]+800;loY=anchor[1]-800;hiY=anchor[1]+800;}
    }

    @Override protected synchronized void onDraw(Canvas c){
        super.onDraw(c);float w=getWidth(),h=getHeight();if(w<=0||h<=0)return;
        String place=snapshot.optString("map_name","Chưa login");int map=snapshot.optInt("map"),channel=snapshot.optInt("channel");
        JSONArray team=snapshot.optJSONArray("team"),entities=snapshot.optJSONArray("entities"),safe=snapshot.optJSONArray("safe");
        double[] anchor=findAnchor(team,map,channel);
        if(anchor==null){text(c,"🗺  "+place+"  •  Phân khu "+channel,18,30,16,gold);text(c,team==null||team.length()==0?"Login bot để xem tọa độ live.":"Đang chờ server trả tọa độ…",18,65,14,Color.LTGRAY);return;}
        updateCamera(anchor);
        plotLeft=18;plotRight=w-18;plotTop=50;plotBottom=Math.max(plotTop+100,h-125);
        drawStatic(c,w,h,map,channel,place,safe);
        float tt=animating?ease(Math.min(1f,(System.currentTimeMillis()-animStart)/(float)ANIM_MS)):1f;
        // ROUTE
        if(route!=null&&route.length()>1){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(5);p.setStrokeCap(Paint.Cap.ROUND);p.setStrokeJoin(Paint.Join.ROUND);p.setColor(Color.rgb(255,215,70));Path line=new Path();for(int i=0;i<route.length();i++){JSONArray q=route.optJSONArray(i);if(q==null)continue;PointF a=prj(q.optDouble(0),q.optDouble(1));if(i==0)line.moveTo(a.x,a.y);else line.lineTo(a.x,a.y);}c.drawPath(line,p);p.setStrokeCap(Paint.Cap.BUTT);}
        // QUAI / NGUOI CHOI (chi ve trong khung -> nhe)
        int mobCount=0,playerCount=0;
        if(entities!=null)for(int i=0;i<entities.length();i++){
            JSONObject e=entities.optJSONObject(i);if(e==null)continue;
            boolean mob="mob".equals(e.optString("kind"));if(mob)mobCount++;else playerCount++;
            long id=e.optLong("id",-1);float[] a=id>=0?entAnim.get(id):null;
            double ex=a==null?e.optDouble("x"):(a[0]+(a[2]-a[0])*tt),ey=a==null?e.optDouble("y"):(a[1]+(a[3]-a[1])*tt);
            if(ex<=0||ey<=0)continue;
            PointF q=prj(ex,ey);
            if(q.x<plotLeft-60||q.x>plotRight+60||q.y<plotTop-60||q.y>plotBottom+60)continue;
            dot(c,q.x,q.y,mob?8:11,mob?Color.rgb(230,75,65):Color.rgb(180,105,245));
            tag(c,(mob?"QUÁI • ":"NGƯỜI • ")+e.optString("name",mob?"Quái":"Người chơi"),q.x+(mob?11:14),q.y-9,mob?11:12,mob?Color.rgb(255,185,155):Color.rgb(225,205,255));
        }
        // MEMBER TRONG TEAM
        int same=0,joined=0;
        if(team!=null)for(int i=0;i<team.length();i++){
            JSONObject a=team.optJSONObject(i);if(a==null)continue;
            boolean here=a.optInt("map")==map&&a.optInt("channel")==channel;if(here)same++;if(a.optBoolean("in_party")||a.optBoolean("leader"))joined++;
            if(!here||a.optInt("x")<=0)continue;
            float[] an=teamAnim.get(a.optString("user"));
            double ex=an==null?a.optDouble("x"):(an[0]+(an[2]-an[0])*tt),ey=an==null?a.optDouble("y"):(an[1]+(an[3]-an[1])*tt);
            PointF q=prj(ex,ey);
            if(q.x<plotLeft-60||q.x>plotRight+60||q.y<plotTop-60||q.y>plotBottom+60)continue;
            boolean lead=a.optBoolean("leader"),qs=a.optBoolean("strategist");
            dot(c,q.x,q.y,lead?19:16,lead?gold:(qs?Color.rgb(75,220,145):Color.rgb(70,170,255)));
            String iv=a.isNull("int")?"?":String.valueOf(a.optInt("int"));
            tag(c,(lead?"LEADER • ":(qs?"QUÂN SƯ • ":"MEMBER • "))+a.optString("name")+" • INT "+iv+" ["+a.optInt("x")+","+a.optInt("y")+"]",q.x+22,q.y-12,14,Color.WHITE);
        }
        if(hasTap){PointF q=prj(tapX,tapY);p.setColor(Color.YELLOW);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);c.drawCircle(q.x,q.y,14,p);c.drawLine(q.x-20,q.y,q.x+20,q.y,p);c.drawLine(q.x,q.y-20,q.x,q.y+20,p);tag(c,"ĐÍCH CHẠM ["+(int)tapX+","+(int)tapY+"]",q.x+18,q.y-15,12,Color.YELLOW);}
        int total=team==null?0:team.length();
        text(c,"Cùng map/khu: "+same+"/"+total+"  •  Trong PT: "+joined+"/"+total+"  •  Quái: "+mobCount+"  •  Người khác: "+playerCount,18,h-88,13,same==total?Color.rgb(90,220,145):Color.rgb(255,135,95));
    }

    @Override public boolean onTouchEvent(MotionEvent e){if(e.getAction()!=MotionEvent.ACTION_UP)return true;if(!hasBounds||e.getX()<plotLeft||e.getX()>plotRight||e.getY()<plotTop||e.getY()>plotBottom)return true;tapX=loX+(e.getX()-plotLeft)/(plotRight-plotLeft)*(hiX-loX);tapY=loY+(e.getY()-plotTop)/(plotBottom-plotTop)*(hiY-loY);hasTap=true;invalidate();if(tapListener!=null)tapListener.onMapTap((int)Math.round(tapX),(int)Math.round(tapY));return true;}

    @Override protected void onDetachedFromWindow(){animating=false;super.onDetachedFromWindow();}
}
