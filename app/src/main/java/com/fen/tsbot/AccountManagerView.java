package com.fen.tsbot;

import android.content.Context;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.text.NumberFormat;
import java.util.Locale;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AccountManagerView extends LinearLayout {
    private JSONArray accounts=new JSONArray(); private int selected=0; private int sectionMode=0;
    private final String[] usernames=new String[5],passwords=new String[5];
    private final boolean[] rememberAccounts=new boolean[5];
    private final SharedPreferences savedAccounts;
    private final LinearLayout tabs,body; private final int gold=Color.rgb(213,168,78),card=Color.rgb(17,29,48);
    private Button setupButton,teleportButton,mapButton,loginButton,outButton;
    private EditText currentUserField,currentPassField;
    private final boolean[] loginPending=new boolean[5];
    private JSONObject mapSnapshots=new JSONObject();
    private TeamMapView liveAccountMap;
    // Man BAN DO full-screen: an title + ScrollView, hien map chiem het khung (co nut quay lai nho).
    private TextView titleView;
    private FrameLayout mapHost;
    private JSONArray mapRoute=new JSONArray(),mapTarget=new JSONArray();
    private final String[] actionMessages={"","","","",""};
    private final boolean[] actionErrors=new boolean[5];
    private boolean channelEditing=false;
    // Spinner Android dong popup neu bat ky parent layout nao bi rebuild. Dashboard poll 2.5s
    // van phai nhan data moi, nhung khi dang o Pet & Skill thi chi cache JSON, khong cham UI.
    private boolean combatEditorLocked=false;
    private final int[] combatEntitySelection={0,0,0,0,0}; // 0=tướng, 1..4=pet mang theo
    // Ban nhap cua ca bo cau hinh. Doi tab chi doi View, tuyet doi khong doc lai server.
    private final boolean[] combatDraftReady=new boolean[5];
    private final String[] combatDraftUser={"","","","",""},combatDraftProfileName={"","","","",""};
    private final int[][] combatDraftSkill=new int[5][5],combatDraftMob=new int[5][5],combatDraftHp=new int[5][5],combatDraftSp=new int[5][5];
    private final boolean[][] combatDraftFlags=new boolean[5][3]; // phuc, dai phuc, ho phu
    // Giu nguyen hai Spinner hop vat pham khi dashboard poll; neu rebuild View thi popup se tu dong dong.
    private boolean bagEditorLocked=false;
    // ScrollView goc cua tab account. Giu lai de khoi phuc vi tri cuon sau moi lan renderBody()
    // (dashboard poll 2.5s truoc day dung lai ca cay View -> tuot len dau hoac nhay xuong cuoi).
    private ScrollView bodyScroll;
    // Cap nhat tui do TAI CHO: giu tham chieu tung o de cap nhat so luong/co khoa ma khong dung lai
    // ca ScrollView (do la nguyen nhan "kho cuon"). Spinner hien khi 1 lenh tui dang chay nen.
    private String bagRenderedUser="";
    private boolean bagLive=false;
    private TextView bagHeader;
    private final java.util.LinkedHashSet<Integer> bagShownSlots=new java.util.LinkedHashSet<>();
    private final Map<Integer,TextView> bagItemViews=new HashMap<>();
    private final Map<Integer,Button> bagLockViews=new HashMap<>();
    private final Map<Integer,ProgressBar> bagSpinners=new HashMap<>();
    private final Map<Integer,List<Button>> bagRowButtons=new HashMap<>();
    // O dang cho server tra loi (dang hien spinner). Dashboard poll 2.5s KHONG duoc mo lai nut
    // cua o nay keo nguoi dung bam lai -> dung trung 2 lan.
    private final java.util.HashSet<Integer> bagPendingSlots=new java.util.HashSet<>();
    private boolean channelDraftReady=false; private int channelDraft=0;
    // Ban nhap cho checkbox "Tu chon phan khu vang": dashboard poll 2.5s rebuild View -> phai giu
    // trang thai nguoi dung vua tick, khong doc lai JSON (chua AP DUNG thi JSON van false).
    private boolean channelAutoDraft=false,channelAutoDraftReady=false;
    // Mỗi account nhớ riêng lò và nhóm đang xem, không nhảy tab khi dashboard refresh.
    private final int[] furnaceStoreSelection={1,1,1,1,1}; // 0=thường, 1=hoàng kim
    private final int[] furnaceCategorySelection={0,0,0,0,0}; // bí cấp, trang bị, kim tỏa
    // Trang thai AUTO do nguoi dung vua bam la nguon UI uu tien. Dashboard poll co the bat dau
    // truoc cu bam va tra ve snapshot cu; neu khong merge theo username no se lam tab vua bat toi
    // lai, hoac trong nhu nut cua tab ke ben vua duoc bat.
    private final Boolean[] localAutoBattle=new Boolean[5],localAutoPursuit=new Boolean[5];
    // Cache optimistic phai thuoc ca SLOT LAN USER. Neu dashboard sap lai/doi account ma chi
    // giu theo slot, trang thai AUTO cua acc cu co the bi ve sang acc ke ben.
    private final String[] localAutoBattleUser=new String[5],localAutoPursuitUser=new String[5];
    public interface AccountActionListener{void onLogin(int slot,String user,String pass);void onAutoBattle(int slot,String user,String pass);void onLogout(int slot,String user);void onTeleport(int slot,String user,int cityId);void onCombatSettings(int slot,String user,int petId,int charSkill,int petSkill,int hpPercent,int spPercent,boolean usePhucThan,boolean useDaiPhucThan,int charMobMin,int petMobMin,int petHpPercent,int petSpPercent,boolean useDgHoPhu,boolean autoBuyBaoHop);void onAccountAction(String user,String action,JSONObject payload);void onChannelPolicy(boolean autoMode,int channel);void onMapTap(int x,int y);void onAutoMode(int slot,String user,String mode);}
    private AccountActionListener actionListener;
    public AccountManagerView(Context c){super(c);savedAccounts=c.getSharedPreferences("tsbot_saved_accounts",Context.MODE_PRIVATE);for(int i=0;i<5;i++){rememberAccounts[i]=savedAccounts.getBoolean("remember_"+i,false);if(rememberAccounts[i]){usernames[i]=savedAccounts.getString("user_"+i,"");passwords[i]=savedAccounts.getString("pass_"+i,"");}}setOrientation(VERTICAL);setPadding(dp(12),dp(10),dp(12),dp(12));setBackgroundColor(Color.rgb(8,17,31));titleView=txt("QUẢN LÝ ACCOUNT",21,gold);titleView.setTypeface(Typeface.DEFAULT_BOLD);addView(titleView);HorizontalScrollView hs=new HorizontalScrollView(c);tabs=new LinearLayout(c);tabs.setOrientation(HORIZONTAL);hs.addView(tabs);hs.setVisibility(GONE);addView(hs,new LayoutParams(-1,0));bodyScroll=new ScrollView(c);ScrollView scroll=bodyScroll;body=new LinearLayout(c);body.setOrientation(VERTICAL);scroll.addView(body);addView(scroll,new LayoutParams(-1,0,1));buildFullScreenMap(c);renderBody();}
    public void setAccountActionListener(AccountActionListener listener){actionListener=listener;updateLoginRequiredButtons();}
    public String configuredUser(int slot){return usernames[slot]==null?"":usernames[slot].trim();}
    public boolean hasPendingLogin(){for(boolean pending:loginPending)if(pending)return true;return false;}
    public void markLoginPending(int slot){loginPending[slot]=true;updateAccountControls();}
    public void clearLoginPending(int slot){if(slot>=0&&slot<5)loginPending[slot]=false;updateAccountControls();}
    public void clearLoginPending(String user){for(int i=0;i<5;i++)if(user==null||user.isEmpty()||user.equals(configuredUser(i)))loginPending[i]=false;updateAccountControls();}
    private void updateAccountControls(){
        JSONObject a=selected<accounts.length()?accounts.optJSONObject(selected):null;
        boolean online=a!=null&&a.optBoolean("online"),connecting=a!=null&&a.optBoolean("logging_in");
        boolean busy=online||connecting||loginPending[selected];
        if(loginButton!=null)loginButton.setEnabled(!busy);
        if(outButton!=null)outButton.setEnabled(online||connecting);
        if(currentUserField!=null){currentUserField.setEnabled(!busy);currentUserField.setAlpha(busy?.65f:1f);}
        if(currentPassField!=null){currentPassField.setEnabled(!busy);currentPassField.setAlpha(busy?.65f:1f);}
    }
    private void styleCredentialField(EditText field){
        field.setHintTextColor(Color.rgb(145,163,186));field.setPadding(dp(14),dp(10),dp(14),dp(10));
        android.graphics.drawable.GradientDrawable bg=new android.graphics.drawable.GradientDrawable();
        bg.setColor(Color.rgb(17,29,48));bg.setCornerRadius(dp(12));bg.setStroke(dp(1),Color.rgb(49,68,91));field.setBackground(bg);
    }
    public JSONArray getConfiguredCredentials(){JSONArray rows=new JSONArray();for(int i=0;i<5;i++){String u=usernames[i]==null?"":usernames[i].trim();if(u.isEmpty())continue;try{rows.put(new JSONObject().put("slot",i).put("u",u).put("p",passwords[i]==null?"":passwords[i]));if(rememberAccounts[i])saveAccount(i,u,passwords[i]==null?"":passwords[i]);}catch(JSONException ignored){}}return rows;}
    public void setActionMessage(String message,boolean error){setActionMessage(selected,message,error);}
    public void setActionMessage(int slot,String message,boolean error){if(slot<0||slot>=5)return;actionMessages[slot]=message==null?"":message;actionErrors[slot]=error;if(slot==selected&&sectionMode!=4&&sectionMode!=1)renderBody();}
    public void setActionMessageForUser(String user,String message,boolean error){for(int i=0;i<5;i++)if(user!=null&&!user.isEmpty()&&user.equals(configuredUser(i))){setActionMessage(i,message,error);return;}}
    public void setChannelPolicyResult(boolean ok,boolean autoMode,int channel,String message){actionMessages[selected]=message==null?"":message;actionErrors[selected]=!ok;if(ok){JSONObject a=selected<accounts.length()?accounts.optJSONObject(selected):null;if(a!=null){try{a.put("channel_auto",autoMode);a.put("channel_manual",channel);}catch(Exception ignored){}}channelDraft=channel;channelDraftReady=true;channelAutoDraft=autoMode;channelAutoDraftReady=true;}channelEditing=false;renderBody();}
    public void setMapSnapshots(JSONObject data){mapSnapshots=data==null?new JSONObject():data;if(sectionMode==5&&!channelEditing){if(liveAccountMap!=null){JSONObject own=mapSnapshots.optJSONObject(getSelectedUser());liveAccountMap.setSnapshot(own);}else renderBody();}}
    public void setMapRoute(JSONArray route,JSONArray target){mapRoute=route==null?new JSONArray():route;mapTarget=target==null?new JSONArray():target;if(sectionMode==5&&liveAccountMap!=null)liveAccountMap.setRoute(mapRoute,mapTarget);}
    // Tao 1 lan: khung map full-screen + nut quay lai. Map tai dung lai, khong tao moi moi lan mo.
    private void buildFullScreenMap(Context c){
        mapHost=new FrameLayout(c);mapHost.setVisibility(GONE);
        liveAccountMap=new TeamMapView(c);
        liveAccountMap.setOnMapTapListener((x,y)->{if(actionListener!=null)actionListener.onMapTap(x,y);});
        mapHost.addView(liveAccountMap,new FrameLayout.LayoutParams(-1,-1));
        Button back=btn("← THÔNG TIN");back.setOnClickListener(v->{sectionMode=0;renderBody();});
        // Goc tren-PHAI de khong de len tieu de map (ve o goc tren-trai trong TeamMapView).
        FrameLayout.LayoutParams blp=new FrameLayout.LayoutParams(dp(136),dp(48));blp.gravity=Gravity.TOP|Gravity.RIGHT;blp.setMargins(0,dp(8),dp(8),0);mapHost.addView(back,blp);
        addView(mapHost,new LayoutParams(-1,0,1));
    }
    public boolean isMapSection(){return sectionMode==5;}
    // Goi tren UI thread (tu refreshMapSnapshot) -> bao bridge co can gui lai luoi va cham khong.
    public boolean mapNeedsTerrain(){return liveAccountMap==null||liveAccountMap.needsTerrain();}
    public String getSelectedUser(){JSONObject a=selected<accounts.length()?accounts.optJSONObject(selected):null;return a==null?"":a.optString("user","");}
    public void toggleAutoOptimistic(int slot,String user,String mode){if(slot<0||slot>=5)return;JSONObject a=slot<accounts.length()?accounts.optJSONObject(slot):null;if(a==null||user==null||!user.equals(a.optString("user")))return;String key="battle".equals(mode)?"auto_battle_enabled":"auto_pursuit_enabled";boolean next=!a.optBoolean(key,false);if("battle".equals(mode)){localAutoBattle[slot]=next;localAutoBattleUser[slot]=user;}else{localAutoPursuit[slot]=next;localAutoPursuitUser[slot]=user;}try{a.put(key,next);}catch(Exception ignored){}if(slot==selected)renderBody();}
    public void setAutoState(int slot,String user,boolean battle,boolean pursuit){if(slot<0||slot>=5||user==null)return;JSONObject a=slot<accounts.length()?accounts.optJSONObject(slot):null;if(a==null||!user.equals(a.optString("user")))return;localAutoBattle[slot]=battle;localAutoPursuit[slot]=pursuit;localAutoBattleUser[slot]=user;localAutoPursuitUser[slot]=user;try{a.put("auto_battle_enabled",battle);a.put("auto_pursuit_enabled",pursuit);}catch(Exception ignored){}if(slot==selected)renderBody();}
    public void selectAccount(int slot){selected=Math.max(0,Math.min(4,slot));sectionMode=0;combatEditorLocked=false;bagEditorLocked=false;channelEditing=false;channelDraftReady=false;channelAutoDraftReady=false;updateLoginRequiredButtons();renderBody();}
public void setData(JSONObject data){JSONArray a=data.optJSONArray("accounts");accounts=a==null?new JSONArray():a;for(int i=0;i<Math.min(5,accounts.length());i++){JSONObject x=accounts.optJSONObject(i);if(x==null)continue;String u=x.optString("user");try{if(localAutoBattle[i]!=null&&u.equals(localAutoBattleUser[i]))x.put("auto_battle_enabled",localAutoBattle[i]);else{localAutoBattle[i]=null;localAutoBattleUser[i]=null;}if(localAutoPursuit[i]!=null&&u.equals(localAutoPursuitUser[i]))x.put("auto_pursuit_enabled",localAutoPursuit[i]);else{localAutoPursuit[i]=null;localAutoPursuitUser[i]=null;}}catch(Exception ignored){}if(usernames[i]==null&&!u.isEmpty())usernames[i]=u;}for(int i=0;i<Math.min(5,accounts.length());i++){JSONObject x=accounts.optJSONObject(i);if(x!=null&&(x.optBoolean("online")||x.optBoolean("logging_in")))loginPending[i]=false;}updateAccountControls();if(sectionMode==5)return;if(sectionMode==1){JSONObject bagAcc=selected<accounts.length()?accounts.optJSONObject(selected):null;if(bagAcc!=null)updateBagLive(bagAcc.optString("user"),bagAcc.optJSONObject("bag"));return;}if(bagEditorLocked||combatEditorLocked||sectionMode==4)return;updateLoginRequiredButtons();renderTabs();JSONObject current=selected<accounts.length()?accounts.optJSONObject(selected):null;boolean selectedOnline=current!=null&&current.optBoolean("online");if(!channelEditing&&(sectionMode==2||sectionMode==3||sectionMode==5||(sectionMode==0&&selectedOnline)||!hasFocus()))renderBody();}
    private void updateLoginRequiredButtons(){JSONObject a=selected<accounts.length()?accounts.optJSONObject(selected):null;boolean online=a!=null&&a.optBoolean("online");if(setupButton!=null)setupButton.setEnabled(online);if(teleportButton!=null)teleportButton.setEnabled(online);if(mapButton!=null)mapButton.setEnabled(online);}
    private void renderTabs(){tabs.removeAllViews();for(int i=0;i<accounts.length();i++){JSONObject a=accounts.optJSONObject(i);Button b=btn((a!=null&&a.optBoolean("online")?"● ":"○ ")+(a==null?"Slot "+(i+1):a.optString("name",a.optString("user"))));final int index=i;b.setTextColor(i==selected?Color.BLACK:Color.WHITE);b.setBackgroundColor(i==selected?gold:card);b.setOnClickListener(v->{selected=index;bagEditorLocked=false;combatEditorLocked=false;renderTabs();renderBody();});tabs.addView(b,new LayoutParams(dp(150),-2));}}
    // Bao quanh renderBodyInner de giu vi tri cuon: dashboard poll / thao tac lam dung lai ca cay View,
    // khong khoi phuc thi ScrollView tuot ve dau (hoac nhay xuong cuoi khi co View xin focus).
    private void renderBody(){
        final int keepY=bodyScroll==null?0:bodyScroll.getScrollY();
        renderBodyInner();
        if(bodyScroll!=null)bodyScroll.post(()->{if(bodyScroll!=null)bodyScroll.scrollTo(0,keepY);});
    }
    private void renderBodyInner(){
        // Roi khoi tab RUONG DO thi bo moi trang thai "dang cho" (khong de spinner treo khi quay lai).
        if(sectionMode!=1)bagPendingSlots.clear();
        body.removeAllViews();loginButton=null;outButton=null;currentUserField=null;currentPassField=null;
        JSONObject a=selected<accounts.length()?accounts.optJSONObject(selected):null;
        if(a==null)a=new JSONObject();
        boolean on=a.optBoolean("online"),logging=a.optBoolean("logging_in");
        // BẢN ĐỒ là màn hình TOÀN KHUNG: an title + ScrollView, hiện mapHost chiếm hết khung.
        if(sectionMode==5){setPadding(0,0,0,0);titleView.setVisibility(GONE);bodyScroll.setVisibility(GONE);mapHost.setVisibility(VISIBLE);renderAccountMap(a);return;}
        setPadding(dp(12),dp(10),dp(12),dp(12));titleView.setVisibility(VISIBLE);bodyScroll.setVisibility(VISIBLE);mapHost.setVisibility(GONE);
        TextView state=txt((on?"● ONLINE":(logging?"◌ ĐANG ĐĂNG NHẬP":"○ OFFLINE"))+"  •  ACCOUNT "+(selected+1)+(a.optString("user").isEmpty()?"":"  •  "+a.optString("name")),16,on?Color.rgb(75,225,140):Color.rgb(255,110,100));
        state.setPadding(0,dp(12),0,dp(8));body.addView(state);
        EditText user=new EditText(getContext()),pass=new EditText(getContext());
        user.setHint("Username account "+(selected+1));pass.setHint("Password");
        user.setText(usernames[selected]==null?a.optString("user"):usernames[selected]);pass.setText(passwords[selected]==null?"":passwords[selected]);
        user.setTextColor(Color.WHITE);pass.setTextColor(Color.WHITE);user.setSingleLine();pass.setSingleLine();pass.setInputType(0x00000081);
        currentUserField=user;currentPassField=pass;styleCredentialField(user);styleCredentialField(pass);
        LayoutParams userLp=new LayoutParams(-1,dp(54)),passLp=new LayoutParams(-1,dp(54));userLp.setMargins(0,dp(6),0,dp(4));passLp.setMargins(0,dp(4),0,dp(6));body.addView(user,userLp);body.addView(pass,passLp);
        CheckBox remember=new CheckBox(getContext());remember.setText("🔒 Lưu tài khoản và mật khẩu trên thiết bị này");remember.setTextColor(Color.WHITE);remember.setChecked(rememberAccounts[selected]);body.addView(remember,new LayoutParams(-1,dp(48)));
        LinearLayout actions=new LinearLayout(getContext());actions.setOrientation(HORIZONTAL);
        Button login=btn("🔑 LOGIN"),logout=btn("⏻ OUT");
        loginButton=login;outButton=logout;updateAccountControls();
        final int slot=selected;
        TextWatcher credentialsWatcher=new TextWatcher(){public void beforeTextChanged(CharSequence s,int start,int count,int after){}public void onTextChanged(CharSequence s,int start,int before,int count){usernames[slot]=user.getText().toString().trim();passwords[slot]=pass.getText().toString();}public void afterTextChanged(Editable e){}};
        user.addTextChangedListener(credentialsWatcher);pass.addTextChangedListener(credentialsWatcher);
        remember.setOnCheckedChangeListener((button,checked)->{rememberAccounts[slot]=checked;if(!checked)clearSavedAccount(slot);});
        login.setOnClickListener(v->{usernames[slot]=user.getText().toString().trim();passwords[slot]=pass.getText().toString();rememberAccounts[slot]=remember.isChecked();if(rememberAccounts[slot])saveAccount(slot,usernames[slot],passwords[slot]);else clearSavedAccount(slot);actionMessages[slot]="Đang gửi yêu cầu đăng nhập "+usernames[slot]+"…";actionErrors[slot]=false;if(actionListener!=null)actionListener.onLogin(slot,usernames[slot],passwords[slot]);renderBody();});
        logout.setOnClickListener(v->{usernames[slot]=user.getText().toString().trim();if(actionListener!=null)actionListener.onLogout(slot,usernames[slot]);});
        actions.addView(login,new LayoutParams(0,-2,1));actions.addView(logout,new LayoutParams(0,-2,1));body.addView(actions);

        String area=a.optString("area_name",a.optString("map_name","Khu vực chưa có tên"));if(area.matches("\\d+"))area="Khu vực chưa có tên";String current=on?"🏙 Thành gần nhất: "+a.optString("city_name","Chưa xác định")+"\n📍 Khu vực hiện tại: "+area+"\n🧭 Tọa độ: X "+a.optInt("x")+"  •  Y "+a.optInt("y")+"  •  Phân khu "+a.optInt("channel"):"📍 Đang ở: Chưa có dữ liệu — account chưa online";
        String train=a.isNull("train_map")||!a.has("train_map")?"🎯 Bãi train: Chưa chọn map và tọa độ":"🎯 Bãi train: "+a.optString("train_map_name","Chưa xác định")+"  •  X "+a.optInt("train_x")+"  Y "+a.optInt("train_y");
        String party="👥 Party hiện tại: "+a.optInt("party_count")+" / "+a.optInt("party_expected")+" thành viên";
        TextView location=txt(current+"\n"+train+"\n"+party,13,Color.rgb(205,220,240));location.setPadding(dp(12),dp(10),dp(12),dp(10));location.setBackgroundColor(Color.rgb(20,38,61));LayoutParams locationLp=new LayoutParams(-1,-2);locationLp.setMargins(0,dp(6),0,dp(8));body.addView(location,locationLp);

        if(a.optBoolean("leader"))renderLeaderChannelPolicy(a,on);

        renderSectionGrid(on,a.optBoolean("leader"));
        String actionMessage=actionMessages[selected];boolean actionError=actionErrors[selected];if(!actionMessage.isEmpty()){TextView msg=txt(actionMessage,13,actionError?Color.rgb(255,110,100):Color.rgb(100,210,255));msg.setPadding(dp(10),dp(10),dp(10),dp(10));msg.setBackgroundColor(card);body.addView(msg,new LayoutParams(-1,-2));}
        if(a.length()==0){body.addView(txt("Nhập tài khoản ngay phía trên rồi bấm LOGIN.",14,Color.LTGRAY));return;}
        if(sectionMode==1)renderBag(a,a.optJSONObject("bag"));else if(sectionMode==2)renderActivityLog(a.optJSONArray("activity_log"));else if(sectionMode==3)renderTeleport(a);else if(sectionMode==4)renderCombatEntitySettings(a);else if(sectionMode==6)renderShop(a);else if(sectionMode==7)renderFurnace(a);else renderInfo(a);
    }

    private void renderLeaderChannelPolicy(JSONObject a,boolean online){if(!channelDraftReady){channelDraft=a.optInt("channel_manual",a.optInt("channel",1));channelDraftReady=true;if(!channelAutoDraftReady){channelAutoDraft=a.optBoolean("channel_auto",false);channelAutoDraftReady=true;}}LinearLayout box=new LinearLayout(getContext());box.setOrientation(VERTICAL);box.setPadding(dp(10),dp(8),dp(10),dp(10));box.setBackgroundColor(card);TextView title=txt("📡 CHỌN PHÂN KHU FARM",14,gold);box.addView(title);JSONArray options=a.optJSONArray("channel_options");List<Integer> ids=new ArrayList<>();List<String> labels=new ArrayList<>();if(options!=null)for(int i=0;i<options.length();i++){JSONObject row=options.optJSONObject(i);if(row==null)continue;int id=row.optInt("id"),cur=row.optInt("current"),cap=row.optInt("capacity");ids.add(id);labels.add(cur>=0&&cap>=0?"Phân khu "+id+"  •  "+cur+"/"+cap+" người":"Phân khu "+id+"  •  sức chứa chưa xác định");}if(ids.isEmpty()){ids.add(Math.max(1,a.optInt("channel",1)));labels.add("Phân khu hiện tại "+ids.get(0)+"  •  đang yêu cầu server cập nhật…");}Spinner channel=new Spinner(getContext());channel.setAdapter(readableAdapter(labels));int saved=ids.indexOf(channelDraft);channel.setSelection(Math.max(0,saved));channel.setEnabled(online);box.addView(channel,new LayoutParams(-1,dp(52)));channel.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int pos,long id){if(pos>=0&&pos<ids.size())channelDraft=ids.get(pos);}public void onNothingSelected(AdapterView<?> p){}});channel.setOnTouchListener((v,e)->{channelEditing=true;return false;});CheckBox autoCh=new CheckBox(getContext());autoCh.setText("🔍 Tự chọn phân khu vắng (ít người nhất, đủ chỗ cho cả team)");autoCh.setTextColor(Color.WHITE);autoCh.setChecked(channelAutoDraft);autoCh.setOnCheckedChangeListener((v,ck)->{channelAutoDraft=ck;channelEditing=true;channel.setEnabled(online&&!ck);});channel.setEnabled(online&&!channelAutoDraft);box.addView(autoCh,new LayoutParams(-1,dp(52)));Button apply=btn("✓ ÁP DỤNG PHÂN KHU FARM");apply.setEnabled(online);apply.setOnClickListener(v->{channelEditing=true;apply.setEnabled(false);apply.setText("◌ ĐANG ÁP DỤNG…");int pos=Math.max(0,channel.getSelectedItemPosition());channelDraft=ids.get(Math.min(pos,ids.size()-1));if(actionListener!=null)actionListener.onChannelPolicy(autoCh.isChecked(),channelDraft);});box.addView(apply,new LayoutParams(-1,dp(54)));TextView note=txt("Danh sách lấy theo map leader đang đứng, tự tải lại khi đổi map và mỗi 5 phút. Chỉ đổi khi bạn bấm ÁP DỤNG.",12,Color.rgb(155,175,200));box.addView(note);LayoutParams lp=new LayoutParams(-1,-2);lp.setMargins(0,0,0,dp(8));body.addView(box,lp);}

    private void renderSectionGrid(boolean online,boolean leader){
        GridLayout grid=new GridLayout(getContext());grid.setColumnCount(3);grid.setRowCount(3);grid.setUseDefaultMargins(false);
        Button info=btn("👤\nTHÔNG TIN"),bag=btn("🎒\nRƯƠNG ĐỒ"),combat=btn("⚔\nNHẬT KÝ"),shop=btn("🛒\nCỬA HÀNG");
        setupButton=btn("🐾\nPET & SKILL");teleportButton=btn("✦\nDỊCH CHUYỂN");mapButton=leader?btn("🗺\nBẢN ĐỒ"):null;
        info.setOnClickListener(v->{bagEditorLocked=false;combatEditorLocked=false;sectionMode=0;renderBody();});bag.setOnClickListener(v->{combatEditorLocked=false;bagEditorLocked=true;sectionMode=1;renderBody();});combat.setOnClickListener(v->{bagEditorLocked=false;combatEditorLocked=false;sectionMode=2;renderBody();});teleportButton.setOnClickListener(v->{bagEditorLocked=false;combatEditorLocked=false;sectionMode=3;renderBody();});setupButton.setOnClickListener(v->{bagEditorLocked=false;sectionMode=4;combatEditorLocked=true;renderBody();});shop.setOnClickListener(v->{bagEditorLocked=false;combatEditorLocked=false;sectionMode=6;renderBody();});if(mapButton!=null)mapButton.setOnClickListener(v->{bagEditorLocked=false;combatEditorLocked=false;sectionMode=5;renderBody();});
        setupButton.setEnabled(online);teleportButton.setEnabled(online);shop.setEnabled(online);if(mapButton!=null)mapButton.setEnabled(online);
        addGridButton(grid,info,sectionMode==0);addGridButton(grid,bag,sectionMode==1);addGridButton(grid,combat,sectionMode==2);addGridButton(grid,setupButton,sectionMode==4);addGridButton(grid,teleportButton,sectionMode==3);addGridButton(grid,shop,sectionMode==6);if(mapButton!=null)addGridButton(grid,mapButton,sectionMode==5);
        body.addView(grid,new LayoutParams(-1,-2));
    }

    private void addGridButton(GridLayout grid,Button button,boolean active){button.setTextSize(10);button.setGravity(Gravity.CENTER);button.setSelected(active);int selectedFill=Color.rgb(36,105,145);button.setBackgroundTintList(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},new int[]{Color.rgb(38,43,52),active?selectedFill:card}));button.setTextColor(button.isEnabled()?Color.WHITE:Color.rgb(112,120,132));GridLayout.LayoutParams lp=new GridLayout.LayoutParams();lp.width=0;lp.height=dp(62);lp.columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f);lp.setMargins(dp(3),dp(3),dp(3),dp(3));grid.addView(button,lp);}

    // Man BAN DO full-screen: chi cap nhat du lieu cho map da tao san (khong dung lai View).
    private void renderAccountMap(JSONObject a){String user=a.optString("user");JSONObject own=mapSnapshots.optJSONObject(user);if(own==null)own=new JSONObject();liveAccountMap.setSnapshot(own);liveAccountMap.setRoute(mapRoute,mapTarget);}
    private void renderTeleport(JSONObject a){body.addView(txt("✦ THÀNH ACCOUNT ĐÃ MỞ",16,gold));if(!a.optBoolean("online")){body.addView(txt("Account cần ONLINE để đọc và dùng danh sách teleport.",14,Color.LTGRAY));return;}JSONArray cities=a.optJSONArray("cities");if(!a.optBoolean("cities_loaded")){body.addView(txt("Đang chờ server trả cờ nhiệm vụ / danh sách thành đã mở…",14,Color.LTGRAY));return;}if(cities==null||cities.length()==0){body.addView(txt("Server chưa xác nhận account đã mở thành teleport nào.",14,Color.LTGRAY));return;}final int slot=selected;final String user=a.optString("user");for(int i=0;i<cities.length();i++){JSONObject city=cities.optJSONObject(i);if(city==null)continue;int cityId=city.optInt("id");Button b=btn("✦  "+city.optString("name","Thành "+cityId)+"   •   Map "+cityId);b.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);b.setPadding(dp(16),0,dp(12),0);b.setOnClickListener(v->{actionMessages[slot]="Đang gửi "+user+" dịch chuyển…";actionErrors[slot]=false;if(actionListener!=null)actionListener.onTeleport(slot,user,cityId);renderBody();});LayoutParams lp=new LayoutParams(-1,dp(58));lp.setMargins(0,dp(5),0,dp(5));body.addView(b,lp);}body.addView(txt("Chỉ account đang chọn dịch chuyển. Teleport giữa chừng có thể làm account rời PT.",12,Color.rgb(155,175,200)));}
    private void renderCombatLog(JSONArray logs){body.addView(txt("NHẬT KÝ EXP RIÊNG ACCOUNT",16,gold));if(logs==null||logs.length()==0){body.addView(txt("Chưa có EXP trận đấu. Bấm AUTO BATTLE và chờ kết thúc một trận.",14,Color.LTGRAY));return;}long charTotal=0,petTotal=0;int visible=Math.min(30,logs.length());for(int i=0;i<visible;i++){JSONObject e=logs.optJSONObject(i);if(e==null)continue;long exp=e.optLong("exp");String who=e.optString("who"),label="character".equals(who)?"NHÂN VẬT":("pet".equals(who)?"PET "+e.optString("pet"):"RAW KIND "+e.optInt("kind"));if("character".equals(who))charTotal+=exp;else if("pet".equals(who))petTotal+=exp;LinearLayout row=new LinearLayout(getContext());row.setPadding(dp(10),dp(10),dp(10),dp(10));row.setBackgroundColor(i%2==0?card:Color.rgb(12,24,41));row.addView(txt(e.optString("time")+"  •  "+label+"\nPacket kind="+e.optInt("kind"),13,Color.WHITE),new LayoutParams(0,-2,1));row.addView(txt("+"+num(exp)+" EXP",16,gold));body.addView(row,new LayoutParams(-1,-2));}body.addView(txt("Trong "+logs.length()+" dòng gần nhất: Nhân vật +"+num(charTotal)+" EXP  •  Pet +"+num(petTotal)+" EXP",13,Color.rgb(130,210,255)));}
    private void renderActivityLog(JSONArray logs){body.addView(txt("NHẬT KÝ EXP • NHẶT • DÙNG VẬT PHẨM",16,gold));if(logs==null||logs.length()==0){body.addView(txt("Chưa có hoạt động mới. Nhật ký bắt đầu ghi từ lúc account login bằng bản này.",14,Color.LTGRAY));return;}long charTotal=0,petTotal=0;int visible=Math.min(30,logs.length());for(int i=0;i<visible;i++){JSONObject e=logs.optJSONObject(i);if(e==null)continue;String type=e.optString("type"),left,right,colorLabel;if("phuc_than".equals(type)){left=e.optString("time")+"  •  PHÚC THẦN";right="Còn "+e.optInt("remaining")+" lượt";colorLabel="phuc";}else if("battle_summary".equals(type)){left=e.optString("time")+"  •  KẾT TRẬN\n"+e.optString("message");right="";colorLabel="exp";}else if("battle_exp".equals(type)){boolean pet="pet".equals(e.optString("who"));long exp=e.optLong("exp");if(pet)petTotal+=exp;else charTotal+=exp;left=e.optString("time")+"  •  "+(pet?"🐾 PET ":"👤 TƯỚNG ")+e.optString("name",pet?e.optString("pet","Pet đang ra trận"):"Nhân vật");right=e.optBoolean("confirmed",exp>0)?"+"+num(exp)+" EXP":"Server chưa cấp EXP";colorLabel="exp";}else if("exp".equals(type)&&"unknown".equals(e.optString("who"))){left=e.optString("time")+"  •  EXP chưa xác định đối tượng";right="+"+num(e.optLong("exp"));colorLabel="exp";}else if("exp".equals(type)){boolean pet="pet".equals(e.optString("who"));long exp=e.optLong("exp");if(pet)petTotal+=exp;else charTotal+=exp;left=e.optString("time")+"  •  "+(pet?"PET "+e.optString("pet"):"NHÂN VẬT");right="+"+num(exp)+" EXP";colorLabel="exp";}else if("loot".equals(type)){left=e.optString("time")+"  •  NHẶT\n"+e.optString("item")+"  ["+e.optInt("item_id")+"]";right="+"+num(e.optInt("qty"));colorLabel="loot";}else{left=e.optString("time")+"  •  ĐÃ GỬI DÙNG\n"+e.optString("item")+" → "+("pet".equals(e.optString("target"))?"PET":"NHÂN VẬT");right="−"+num(e.optInt("qty"));colorLabel="use";}LinearLayout row=new LinearLayout(getContext());row.setPadding(dp(10),dp(10),dp(10),dp(10));row.setBackgroundColor(i%2==0?card:Color.rgb(12,24,41));row.addView(txt(left,13,Color.WHITE),new LayoutParams(0,-2,1));row.addView(txt(right,15,"loot".equals(colorLabel)?Color.rgb(90,225,145):("use".equals(colorLabel)?Color.rgb(255,150,95):("phuc".equals(colorLabel)?Color.rgb(115,205,255):gold))));body.addView(row,new LayoutParams(-1,-2));}body.addView(txt("30 dòng gần nhất: NV +"+num(charTotal)+" EXP  •  Pet +"+num(petTotal)+" EXP",13,Color.rgb(130,210,255)));}
    private void renderCombatSettings(JSONObject a){body.addView(txt("⚙ PET • SKILL • TỰ DÙNG HP/SP",16,gold));if(!a.optBoolean("online")){body.addView(txt("Hãy LOGIN account để lấy pet và skill thật từ server.",14,Color.LTGRAY));return;}JSONObject skills=a.optJSONObject("skills");if(skills==null)skills=new JSONObject();JSONArray chars=skills.optJSONArray("char"),pets=skills.optJSONArray("pets");List<Integer> charIds=new ArrayList<>(),petIds=new ArrayList<>();List<String> charNames=new ArrayList<>(),petNames=new ArrayList<>();charIds.add(0);charNames.add("Tự động chọn skill nhân vật");petIds.add(0);petNames.add("Giữ pet hiện tại / tự động");if(chars!=null)for(int i=0;i<chars.length();i++){JSONArray s=chars.optJSONArray(i);if(s!=null){charIds.add(s.optInt(0));charNames.add(s.optString(1,"Skill "+s.optInt(0))+"  ["+s.optInt(0)+"]");}}if(pets!=null)for(int i=0;i<pets.length();i++){JSONArray p=pets.optJSONArray(i);if(p!=null){petIds.add(p.optInt(0));petNames.add(p.optString(1,"Pet "+p.optInt(0))+(p.optInt(0)==skills.optInt("active")?"  •  ĐANG RA TRẬN":""));}}body.addView(txt("Pet xuất trận",13,Color.WHITE));Spinner pet=new Spinner(getContext());pet.setAdapter(readableAdapter(petNames));int activeIndex=petIds.indexOf(skills.optInt("active"));pet.setSelection(Math.max(0,activeIndex));body.addView(pet,new LayoutParams(-1,dp(52)));body.addView(txt("Skill nhân vật",13,Color.WHITE));Spinner charSkill=new Spinner(getContext());charSkill.setAdapter(readableAdapter(charNames));body.addView(charSkill,new LayoutParams(-1,dp(52)));body.addView(txt("Skill pet",13,Color.WHITE));Spinner petSkill=new Spinner(getContext());body.addView(petSkill,new LayoutParams(-1,dp(52)));List<Integer> petSkillIds=new ArrayList<>();pet.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> parent,View view,int pos,long id){petSkillIds.clear();List<String> names=new ArrayList<>();petSkillIds.add(0);names.add("Tự động chọn skill pet");int pid=petIds.get(pos);if(pets!=null)for(int i=0;i<pets.length();i++){JSONArray pr=pets.optJSONArray(i);if(pr!=null&&pr.optInt(0)==pid){JSONArray ss=pr.optJSONArray(2);if(ss!=null)for(int j=0;j<ss.length();j++){JSONArray s=ss.optJSONArray(j);if(s!=null){petSkillIds.add(s.optInt(0));names.add(s.optString(1,"Skill "+s.optInt(0))+"  ["+s.optInt(0)+"]");}}break;}}petSkill.setAdapter(readableAdapter(names));}public void onNothingSelected(AdapterView<?> parent){}});JSONObject heal=a.optJSONObject("heal");int hp=heal==null?40:(int)Math.round(heal.optDouble("hp_char",.4)*100),sp=heal==null?0:(int)Math.round(heal.optDouble("sp_char",0)*100);TextView hpLabel=txt("Tướng dùng HP khi máu dưới "+hp+"%",13,Color.WHITE),spLabel=txt("Tướng dùng SP khi mana dưới "+sp+"%  (0% = tắt)",13,Color.WHITE);SeekBar hpBar=new SeekBar(getContext()),spBar=new SeekBar(getContext());hpBar.setMax(100);spBar.setMax(100);hpBar.setProgress(hp);spBar.setProgress(sp);hpBar.setOnSeekBarChangeListener(seek(hpLabel,"Tướng dùng HP khi máu dưới ","%"));spBar.setOnSeekBarChangeListener(seek(spLabel,"Tướng dùng SP khi mana dưới ","%  (0% = tắt)"));body.addView(hpLabel);body.addView(hpBar);body.addView(spLabel);body.addView(spBar);CheckBox phucThan=new CheckBox(getContext());phucThan.setText("💎 Tự ăn Phúc Thần");phucThan.setTextColor(Color.WHITE);phucThan.setChecked(a.optBoolean("use_phuc_than",false));body.addView(phucThan,new LayoutParams(-1,dp(52)));
        CheckBox daiPhucThan=new CheckBox(getContext());daiPhucThan.setText("✨ Tự ăn Đại Phúc Thần");daiPhucThan.setTextColor(Color.WHITE);daiPhucThan.setChecked(a.optBoolean("use_dai_phuc_than",false));body.addView(daiPhucThan,new LayoutParams(-1,dp(52)));
        CheckBox dgHoPhu=new CheckBox(getContext());dgHoPhu.setText("Tự ăn Dị Giới Hộ Phù");dgHoPhu.setTextColor(Color.WHITE);dgHoPhu.setChecked(a.optBoolean("use_digioi_ho_phu",false));body.addView(dgHoPhu,new LayoutParams(-1,dp(52)));
        CheckBox autoBaoHop=new CheckBox(getContext());autoBaoHop.setText("Tự mua Túi Triệu Gọi");autoBaoHop.setTextColor(Color.WHITE);autoBaoHop.setChecked(a.optBoolean("auto_buy_bao_hop",false));body.addView(autoBaoHop,new LayoutParams(-1,dp(52)));
        TextView phucRemain=txt("Lượt Phúc Thần server báo: "+(a.isNull("phuc_than_remaining")?"chưa đồng bộ":a.optInt("phuc_than_remaining")+" lượt"),12,Color.rgb(150,200,255));body.addView(phucRemain);Button save=btn("✓ ÁP DỤNG CHO ACCOUNT NÀY");final int slot=selected;final String user=a.optString("user");save.setOnClickListener(v->{int pi=pet.getSelectedItemPosition(),ci=charSkill.getSelectedItemPosition(),psi=petSkill.getSelectedItemPosition();if(actionListener!=null)actionListener.onCombatSettings(slot,user,petIds.get(Math.max(0,pi)),charIds.get(Math.max(0,ci)),petSkillIds.get(Math.max(0,psi)),hpBar.getProgress(),spBar.getProgress(),phucThan.isChecked(),daiPhucThan.isChecked(),4,4,hpBar.getProgress(),spBar.getProgress(),dgHoPhu.isChecked(),autoBaoHop.isChecked());});body.addView(save,new LayoutParams(-1,dp(60)));body.addView(txt("Bot dùng vật phẩm HP/SP đã học từ túi đồ sau trận. Phúc Thần chỉ được dùng khi đã tick. Đổi pet sẽ chờ hết trận rồi mới gửi lệnh.",12,Color.rgb(155,175,200)));}

    private void renderCombatSettingsSaved(JSONObject a){
        body.addView(txt("⚙ PET • SKILL • TỰ DÙNG HP/SP",16,gold));
        if(!a.optBoolean("online")){body.addView(txt("Hãy LOGIN account để lấy pet và skill thật từ server.",14,Color.LTGRAY));return;}
        JSONObject saved=a.optJSONObject("combat_settings");if(saved==null)saved=new JSONObject();
        final int savedPet=saved.optInt("pet_id",0),savedChar=saved.optInt("char_skill",0),savedPetSkill=saved.optInt("pet_skill",0),savedCharMob=Math.max(1,saved.optInt("char_mob_min",4)),savedPetMob=Math.max(1,saved.optInt("pet_mob_min",4));
        JSONObject skills=a.optJSONObject("skills");if(skills==null)skills=new JSONObject();
        final JSONArray pets=skills.optJSONArray("pets");JSONArray chars=skills.optJSONArray("char");
        final List<Integer> petIds=new ArrayList<>(),petSkillIds=new ArrayList<>();List<Integer> charIds=new ArrayList<>();
        List<String> petNames=new ArrayList<>(),charNames=new ArrayList<>();petIds.add(0);petNames.add("Giữ pet hiện tại / tự động");charIds.add(0);charNames.add("Mặc định / tự động");charIds.add(-1);charNames.add("Đánh thường");
        if(chars!=null)for(int i=0;i<chars.length();i++){JSONArray s=chars.optJSONArray(i);if(s!=null){charIds.add(s.optInt(0));charNames.add(s.optString(1,"Skill "+s.optInt(0))+"  ["+s.optInt(0)+"]");}}
        if(pets!=null)for(int i=0;i<pets.length();i++){JSONArray p=pets.optJSONArray(i);if(p!=null){petIds.add(p.optInt(0));petNames.add(p.optString(1,"Pet "+p.optInt(0))+(p.optInt(0)==skills.optInt("active")?"  •  ĐANG RA TRẬN":""));}}
        body.addView(txt("Pet xuất trận",13,Color.WHITE));Spinner pet=new Spinner(getContext());pet.setAdapter(readableAdapter(petNames));int pi=petIds.indexOf(savedPet);if(pi<0)pi=petIds.indexOf(skills.optInt("active"));pet.setSelection(Math.max(0,pi));body.addView(pet,new LayoutParams(-1,dp(52)));
        HorizontalScrollView entityScroll=new HorizontalScrollView(getContext());LinearLayout entityTabs=new LinearLayout(getContext());entityTabs.setOrientation(HORIZONTAL);Button charTab=btn("👤 TƯỚNG");charTab.setOnClickListener(v->{pet.setSelection(0);Toast.makeText(getContext(),"Đang chỉnh cấu hình nhân vật",Toast.LENGTH_SHORT).show();});entityTabs.addView(charTab,new LayoutParams(dp(112),dp(48)));if(pets!=null)for(int i=0;i<Math.min(4,pets.length());i++){JSONArray petRow=pets.optJSONArray(i);if(petRow==null)continue;int petId=petRow.optInt(0),petPos=petIds.indexOf(petId);Button petTab=btn("🐾 "+petRow.optString(1,"PET "+(i+1)));petTab.setOnClickListener(v->{pet.setSelection(Math.max(0,petPos));Toast.makeText(getContext(),"Đang chỉnh "+petRow.optString(1,"pet"),Toast.LENGTH_SHORT).show();});entityTabs.addView(petTab,new LayoutParams(dp(132),dp(48)));}entityScroll.addView(entityTabs);body.addView(entityScroll,new LayoutParams(-1,dp(52)));
        body.addView(txt("Skill nhân vật",13,Color.WHITE));Spinner charSkill=new Spinner(getContext());charSkill.setAdapter(readableAdapter(charNames));charSkill.setSelection(Math.max(0,charIds.indexOf(savedChar)));body.addView(charSkill,new LayoutParams(-1,dp(52)));
        body.addView(txt("Skill pet",13,Color.WHITE));Spinner petSkill=new Spinner(getContext());body.addView(petSkill,new LayoutParams(-1,dp(52)));
        pet.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> parent,View view,int pos,long id){petSkillIds.clear();List<String> names=new ArrayList<>();petSkillIds.add(0);names.add("Mặc định / tự động");petSkillIds.add(-1);names.add("Đánh thường");int pid=petIds.get(Math.max(0,pos));if(pets!=null)for(int i=0;i<pets.length();i++){JSONArray row=pets.optJSONArray(i);if(row!=null&&row.optInt(0)==pid){JSONArray ss=row.optJSONArray(2);if(ss!=null)for(int j=0;j<ss.length();j++){JSONArray s=ss.optJSONArray(j);if(s!=null){petSkillIds.add(s.optInt(0));names.add(s.optString(1,"Skill "+s.optInt(0))+"  ["+s.optInt(0)+"]");}}break;}}petSkill.setAdapter(readableAdapter(names));petSkill.setSelection(Math.max(0,petSkillIds.indexOf(savedPetSkill)));}public void onNothingSelected(AdapterView<?> parent){}});
        List<String> mobChoices=new ArrayList<>();for(int n=1;n<=10;n++)mobChoices.add("Từ "+n+" quái: dùng skill • ít hơn: đánh thường");
        body.addView(txt("Rule skill nhân vật",13,Color.WHITE));Spinner charMob=new Spinner(getContext());charMob.setAdapter(readableAdapter(mobChoices));charMob.setSelection(Math.min(9,savedCharMob-1));body.addView(charMob,new LayoutParams(-1,dp(52)));
        body.addView(txt("Rule skill pet",13,Color.WHITE));Spinner petMob=new Spinner(getContext());petMob.setAdapter(readableAdapter(mobChoices));petMob.setSelection(Math.min(9,savedPetMob-1));body.addView(petMob,new LayoutParams(-1,dp(52)));
        JSONObject heal=a.optJSONObject("heal");int hp=heal==null?70:(int)Math.round(heal.optDouble("hp_char",.7)*100),sp=heal==null?70:(int)Math.round(heal.optDouble("sp_char",.7)*100);
        TextView hpLabel=txt("Tướng dùng HP khi máu dưới "+hp+"%",13,Color.WHITE),spLabel=txt("Tướng dùng SP khi mana dưới "+sp+"%",13,Color.WHITE);SeekBar hpBar=new SeekBar(getContext()),spBar=new SeekBar(getContext());hpBar.setMax(100);spBar.setMax(100);hpBar.setProgress(hp);spBar.setProgress(sp);hpBar.setOnSeekBarChangeListener(seek(hpLabel,"Tướng dùng HP khi máu dưới ","%"));spBar.setOnSeekBarChangeListener(seek(spLabel,"Tướng dùng SP khi mana dưới ","%"));body.addView(hpLabel);body.addView(hpBar);body.addView(spLabel);body.addView(spBar);
        int petHp=heal==null?70:(int)Math.round(heal.optDouble("hp_pet",.7)*100),petSp=heal==null?70:(int)Math.round(heal.optDouble("sp_pet",.7)*100);
        TextView petHpLabel=txt("Pet dùng HP khi máu dưới "+petHp+"%",13,Color.WHITE),petSpLabel=txt("Pet dùng SP khi mana dưới "+petSp+"%",13,Color.WHITE);
        SeekBar petHpBar=new SeekBar(getContext()),petSpBar=new SeekBar(getContext());petHpBar.setMax(100);petSpBar.setMax(100);petHpBar.setProgress(petHp);petSpBar.setProgress(petSp);
        petHpBar.setOnSeekBarChangeListener(seek(petHpLabel,"Pet dùng HP khi máu dưới ","%"));petSpBar.setOnSeekBarChangeListener(seek(petSpLabel,"Pet dùng SP khi mana dưới ","%"));body.addView(petHpLabel);body.addView(petHpBar);body.addView(petSpLabel);body.addView(petSpBar);
        CheckBox phucThan=new CheckBox(getContext());phucThan.setText("💎 Sử dụng Phúc Thần");phucThan.setTextColor(Color.WHITE);phucThan.setChecked(a.optBoolean("use_phuc_than",false));body.addView(phucThan,new LayoutParams(-1,dp(52)));
        CheckBox daiPhucThan=new CheckBox(getContext());daiPhucThan.setText("✨ Tự ăn Đại Phúc Thần");daiPhucThan.setTextColor(Color.WHITE);daiPhucThan.setChecked(a.optBoolean("use_dai_phuc_than",false));body.addView(daiPhucThan,new LayoutParams(-1,dp(52)));
        CheckBox dgHoPhu=new CheckBox(getContext());dgHoPhu.setText("Tự ăn Dị Giới Hộ Phù");dgHoPhu.setTextColor(Color.WHITE);dgHoPhu.setChecked(a.optBoolean("use_digioi_ho_phu",false));body.addView(dgHoPhu,new LayoutParams(-1,dp(52)));
        // Túi Triệu Gọi chỉ mua thủ công trong Cửa hàng; không còn công tắc tự mua ở chiến đấu.
        CheckBox autoBaoHop=new CheckBox(getContext());autoBaoHop.setChecked(false);
        final String profileKey="combat_profiles_"+a.optString("user"),selectedProfileKey="combat_profile_selected_"+a.optString("user");JSONArray loaded;try{loaded=new JSONArray(savedAccounts.getString(profileKey,"[]"));}catch(Exception e){loaded=new JSONArray();}final JSONArray profiles=loaded;
        List<String> profileNames=new ArrayList<>();profileNames.add("Mặc định / không chọn");for(int i=0;i<profiles.length();i++){JSONObject p=profiles.optJSONObject(i);profileNames.add(p==null?"Cấu hình "+(i+1):p.optString("name","Cấu hình "+(i+1)));}
        body.addView(txt("Cấu hình skill",13,Color.WHITE));Spinner profileSpinner=new Spinner(getContext());profileSpinner.setAdapter(readableAdapter(profileNames));String selectedProfileName=savedAccounts.getString(selectedProfileKey,"");int savedProfilePos=profileNames.indexOf(selectedProfileName);profileSpinner.setSelection(Math.max(0,savedProfilePos));body.addView(profileSpinner,new LayoutParams(-1,dp(52)));
        EditText profileName=new EditText(getContext());profileName.setHint("Tên cấu hình mới");profileName.setHintTextColor(Color.rgb(145,163,186));profileName.setTextColor(Color.WHITE);body.addView(profileName,new LayoutParams(-1,dp(52)));
        LinearLayout profileButtons=new LinearLayout(getContext());Button loadProfile=btn("ÁP DỤNG CẤU HÌNH"),saveProfile=btn("LƯU CẤU HÌNH");profileButtons.addView(loadProfile,new LayoutParams(0,dp(54),1));profileButtons.addView(saveProfile,new LayoutParams(0,dp(54),1));body.addView(profileButtons);
        Button deleteProfile=btn("🗑 XÓA CẤU HÌNH ĐÃ CHỌN");deleteProfile.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(150,55,65)));deleteProfile.setOnClickListener(v->{int index=profileSpinner.getSelectedItemPosition()-1;if(index<0){Toast.makeText(getContext(),"Cấu hình mặc định không thể xóa",Toast.LENGTH_SHORT).show();return;}JSONObject selectedProfile=profiles.optJSONObject(index);String name=selectedProfile==null?("Cấu hình "+(index+1)):selectedProfile.optString("name","Cấu hình "+(index+1));new AlertDialog.Builder(getContext()).setTitle("Xóa cấu hình?").setMessage("Xóa ‘"+name+"’ khỏi account này? Thiết lập đang áp dụng cho bot sẽ không bị thay đổi.").setNegativeButton("HỦY",null).setPositiveButton("XÓA",(dialog,which)->{profiles.remove(index);savedAccounts.edit().putString(profileKey,profiles.toString()).remove(selectedProfileKey).apply();Toast.makeText(getContext(),"Đã xóa cấu hình "+name,Toast.LENGTH_SHORT).show();combatEditorLocked=false;renderBody();}).show();});LayoutParams deleteProfileLp=new LayoutParams(-1,dp(52));deleteProfileLp.setMargins(0,dp(5),0,dp(7));body.addView(deleteProfile,deleteProfileLp);
        loadProfile.setOnClickListener(v->{int index=profileSpinner.getSelectedItemPosition()-1;if(index<0){savedAccounts.edit().remove(selectedProfileKey).apply();profileName.setText("");Toast.makeText(getContext(),"Dùng thiết lập mặc định",Toast.LENGTH_SHORT).show();return;}JSONObject p=profiles.optJSONObject(index);if(p==null)return;profileName.setText(p.optString("name"));savedAccounts.edit().putString(selectedProfileKey,p.optString("name")).apply();pet.setSelection(Math.max(0,petIds.indexOf(p.optInt("pet_id",0))));charSkill.setSelection(Math.max(0,charIds.indexOf(p.optInt("char_skill",0))));charMob.setSelection(Math.max(0,Math.min(9,p.optInt("char_mob_min",4)-1)));petMob.setSelection(Math.max(0,Math.min(9,p.optInt("pet_mob_min",4)-1)));hpBar.setProgress(p.optInt("hp",70));spBar.setProgress(p.optInt("sp",70));petHpBar.setProgress(p.optInt("pet_hp",70));petSpBar.setProgress(p.optInt("pet_sp",70));phucThan.setChecked(p.optBoolean("phuc"));daiPhucThan.setChecked(p.optBoolean("dai_phuc"));dgHoPhu.setChecked(p.optBoolean("dg_ho_phu"));autoBaoHop.setChecked(false);petSkill.postDelayed(()->petSkill.setSelection(Math.max(0,petSkillIds.indexOf(p.optInt("pet_skill",0)))),100);});
        if(savedProfilePos>0)profileSpinner.post(loadProfile::performClick);
        saveProfile.setOnClickListener(v->{String name=profileName.getText().toString().trim();if(name.isEmpty()){Toast.makeText(getContext(),"Hãy đặt tên cấu hình",Toast.LENGTH_SHORT).show();return;}try{JSONObject p=new JSONObject();p.put("name",name);p.put("pet_id",petIds.get(Math.max(0,pet.getSelectedItemPosition())));p.put("char_skill",charIds.get(Math.max(0,charSkill.getSelectedItemPosition())));p.put("pet_skill",petSkillIds.get(Math.max(0,petSkill.getSelectedItemPosition())));p.put("char_mob_min",charMob.getSelectedItemPosition()+1);p.put("pet_mob_min",petMob.getSelectedItemPosition()+1);p.put("hp",hpBar.getProgress());p.put("sp",spBar.getProgress());p.put("pet_hp",petHpBar.getProgress());p.put("pet_sp",petSpBar.getProgress());p.put("phuc",phucThan.isChecked());p.put("dai_phuc",daiPhucThan.isChecked());p.put("dg_ho_phu",dgHoPhu.isChecked());p.put("bao_hop",false);int existing=profileSpinner.getSelectedItemPosition()-1;for(int i=0;i<profiles.length();i++){JSONObject old=profiles.optJSONObject(i);if(old!=null&&name.equalsIgnoreCase(old.optString("name"))){existing=i;break;}}if(existing>=0)profiles.put(existing,p);else profiles.put(p);savedAccounts.edit().putString(profileKey,profiles.toString()).putString(selectedProfileKey,name).apply();Toast.makeText(getContext(),"Đã lưu "+name,Toast.LENGTH_SHORT).show();combatEditorLocked=false;renderBody();}catch(Exception e){Toast.makeText(getContext(),"Không lưu được cấu hình",Toast.LENGTH_LONG).show();}});
        Button save=btn("✓ ÁP DỤNG CHO ACCOUNT NÀY");final int slot=selected;final String user=a.optString("user");save.setOnClickListener(v->{int p=pet.getSelectedItemPosition(),c=charSkill.getSelectedItemPosition(),ps=petSkill.getSelectedItemPosition();int selectedPet=petIds.get(Math.max(0,p)),selectedCharSkill=charIds.get(Math.max(0,c)),selectedPetSkill=petSkillIds.get(Math.max(0,ps)),selectedCharMob=charMob.getSelectedItemPosition()+1,selectedPetMob=petMob.getSelectedItemPosition()+1;try{JSONObject local=new JSONObject();local.put("pet_id",selectedPet);local.put("char_skill",selectedCharSkill);local.put("pet_skill",selectedPetSkill);local.put("char_mob_min",selectedCharMob);local.put("pet_mob_min",selectedPetMob);a.put("combat_settings",local);a.put("use_phuc_than",phucThan.isChecked());a.put("use_dai_phuc_than",daiPhucThan.isChecked());JSONObject localHeal=new JSONObject();localHeal.put("hp_char",hpBar.getProgress()/100.0);localHeal.put("sp_char",spBar.getProgress()/100.0);localHeal.put("hp_pet",petHpBar.getProgress()/100.0);localHeal.put("sp_pet",petSpBar.getProgress()/100.0);a.put("heal",localHeal);}catch(Exception ignored){}actionMessages[slot]="Đang lưu pet, skill và rule cho "+user+"…";actionErrors[slot]=false;save.setEnabled(false);save.setText("✓ ĐÃ GỬI CẤU HÌNH — KHÔNG RESET MÀN HÌNH");if(actionListener!=null)actionListener.onCombatSettings(slot,user,selectedPet,selectedCharSkill,selectedPetSkill,hpBar.getProgress(),spBar.getProgress(),phucThan.isChecked(),daiPhucThan.isChecked(),selectedCharMob,selectedPetMob,petHpBar.getProgress(),petSpBar.getProgress(),dgHoPhu.isChecked(),autoBaoHop.isChecked());});body.addView(save,new LayoutParams(-1,dp(60)));body.addView(txt("Thiết lập và rule số quái được lưu riêng theo account. Màn hình được khóa refresh khi đang chỉnh để dropdown và thanh HP/SP không bị reset.",12,Color.rgb(155,175,200)));
    }

    private void renderCombatEntitySettings(JSONObject a){
        body.addView(txt("⚙ CẤU HÌNH TƯỚNG & PET",16,gold));
        if(!a.optBoolean("online")){body.addView(txt("Hãy LOGIN account để lấy pet và skill thật từ server.",14,Color.LTGRAY));return;}
        JSONObject skills=a.optJSONObject("skills");if(skills==null)skills=new JSONObject();
        final JSONArray pets=skills.optJSONArray("pets");final int petCount=Math.min(4,pets==null?0:pets.length());
        int entity=combatEntitySelection[selected];if(entity<0||entity>petCount)entity=0;combatEntitySelection[selected]=entity;
        final int currentEntity=entity;final int slot=selected;final String user=a.optString("user");
        HorizontalScrollView scroll=new HorizontalScrollView(getContext());LinearLayout tabs=new LinearLayout(getContext());tabs.setOrientation(HORIZONTAL);
        Button characterTab=btn("👤 "+a.optString("name","TƯỚNG"));styleEntityTab(characterTab,currentEntity==0);characterTab.setOnClickListener(v->{combatEntitySelection[slot]=0;combatEditorLocked=true;renderBody();});tabs.addView(characterTab,new LayoutParams(dp(145),dp(52)));
        for(int i=0;i<petCount;i++){JSONArray row=pets.optJSONArray(i);if(row==null)continue;final int tabIndex=i+1;Button tab=btn("🐾 "+row.optString(1,"PET "+tabIndex));styleEntityTab(tab,currentEntity==tabIndex);tab.setOnClickListener(v->{combatEntitySelection[slot]=tabIndex;combatEditorLocked=true;renderBody();});tabs.addView(tab,new LayoutParams(dp(145),dp(52)));}
        scroll.addView(tabs);body.addView(scroll,new LayoutParams(-1,dp(58)));

        JSONObject saved=a.optJSONObject("combat_settings");if(saved==null)saved=new JSONObject();JSONObject heal=a.optJSONObject("heal");if(heal==null)heal=new JSONObject();
        final int savedCharSkill=saved.optInt("char_skill",0),savedCharMob=Math.max(1,saved.optInt("char_mob_min",4)),savedPetMob=Math.max(1,saved.optInt("pet_mob_min",4));
        final int charHp=(int)Math.round(heal.optDouble("hp_char",.7)*100),charSp=(int)Math.round(heal.optDouble("sp_char",.7)*100),petHp=(int)Math.round(heal.optDouble("hp_pet",.7)*100),petSp=(int)Math.round(heal.optDouble("sp_pet",.7)*100);
        final boolean phuc=a.optBoolean("use_phuc_than",false),daiPhuc=a.optBoolean("use_dai_phuc_than",false),hoPhu=a.optBoolean("use_digioi_ho_phu",false);
        if(!combatDraftReady[slot]||!user.equals(combatDraftUser[slot])){combatDraftReady[slot]=true;combatDraftUser[slot]=user;combatDraftProfileName[slot]="";combatDraftSkill[slot][0]=savedCharSkill;combatDraftMob[slot][0]=savedCharMob;combatDraftHp[slot][0]=charHp;combatDraftSp[slot][0]=charSp;for(int i=1;i<=4;i++){combatDraftSkill[slot][i]=0;combatDraftMob[slot][i]=savedPetMob;combatDraftHp[slot][i]=petHp;combatDraftSp[slot][i]=petSp;}int configuredPet=saved.optInt("pet_id",0);if(pets!=null)for(int i=0;i<petCount;i++){JSONArray row=pets.optJSONArray(i);if(row!=null&&row.optInt(0)==configuredPet)combatDraftSkill[slot][i+1]=saved.optInt("pet_skill",0);}combatDraftFlags[slot][0]=phuc;combatDraftFlags[slot][1]=daiPhuc;combatDraftFlags[slot][2]=hoPhu;}
        final int entityId;final String entityName;final JSONArray entitySkills;
        if(currentEntity==0){entityId=0;entityName=a.optString("name",user);entitySkills=skills.optJSONArray("char");}else{JSONArray row=pets.optJSONArray(currentEntity-1);entityId=row==null?0:row.optInt(0);entityName=row==null?("Pet "+currentEntity):row.optString(1,"Pet "+currentEntity);entitySkills=row==null?null:row.optJSONArray(2);}
        TextView heading=txt((currentEntity==0?"👤 TƯỚNG • ":"🐾 PET "+currentEntity+" • ")+entityName,15,Color.WHITE);heading.setTypeface(Typeface.DEFAULT_BOLD);heading.setPadding(0,dp(10),0,dp(6));body.addView(heading);
        List<Integer> skillIds=new ArrayList<>();List<String> skillNames=new ArrayList<>();skillIds.add(0);skillNames.add("Mặc định / tự động");skillIds.add(-1);skillNames.add("Đánh thường");if(entitySkills!=null)for(int i=0;i<entitySkills.length();i++){JSONArray row=entitySkills.optJSONArray(i);if(row!=null){skillIds.add(row.optInt(0));skillNames.add(row.optString(1,"Skill "+row.optInt(0))+"  ["+row.optInt(0)+"]");}}
        body.addView(txt(currentEntity==0?"Skill của tướng":"Skill của "+entityName,13,Color.WHITE));Spinner skill=new Spinner(getContext());skill.setAdapter(readableAdapter(skillNames));skill.setSelection(Math.max(0,skillIds.indexOf(combatDraftSkill[slot][currentEntity])));body.addView(skill,new LayoutParams(-1,dp(52)));
        List<String> mobChoices=new ArrayList<>();for(int n=1;n<=10;n++)mobChoices.add("Từ "+n+" quái: dùng skill • ít hơn: đánh thường");body.addView(txt("Rule sử dụng skill",13,Color.WHITE));Spinner mob=new Spinner(getContext());mob.setAdapter(readableAdapter(mobChoices));mob.setSelection(Math.min(9,combatDraftMob[slot][currentEntity]-1));body.addView(mob,new LayoutParams(-1,dp(52)));
        int hp=combatDraftHp[slot][currentEntity],sp=combatDraftSp[slot][currentEntity];String who=currentEntity==0?"Tướng":entityName;
        TextView hpLabel=txt(who+" dùng HP khi máu dưới "+hp+"%",13,Color.WHITE),spLabel=txt(who+" dùng SP khi mana dưới "+sp+"%",13,Color.WHITE);SeekBar hpBar=new SeekBar(getContext()),spBar=new SeekBar(getContext());hpBar.setMax(100);spBar.setMax(100);hpBar.setProgress(hp);spBar.setProgress(sp);hpBar.setOnSeekBarChangeListener(seek(hpLabel,who+" dùng HP khi máu dưới ","%"));spBar.setOnSeekBarChangeListener(seek(spLabel,who+" dùng SP khi mana dưới ","%"));body.addView(hpLabel);body.addView(hpBar);body.addView(spLabel);body.addView(spBar);
        final CheckBox phucBox=new CheckBox(getContext()),daiBox=new CheckBox(getContext()),hoPhuBox=new CheckBox(getContext());phucBox.setChecked(combatDraftFlags[slot][0]);daiBox.setChecked(combatDraftFlags[slot][1]);hoPhuBox.setChecked(combatDraftFlags[slot][2]);
        if(currentEntity==0){phucBox.setText("💎 Sử dụng Phúc Thần");daiBox.setText("✨ Tự ăn Đại Phúc Thần");hoPhuBox.setText("🧿 Tự ăn Dị Giới Hộ Phù");for(CheckBox box:new CheckBox[]{phucBox,daiBox,hoPhuBox}){box.setTextColor(Color.WHITE);body.addView(box,new LayoutParams(-1,dp(50)));}body.addView(txt("Lượt Phúc Thần server báo: "+(a.isNull("phuc_than_remaining")?"chưa đồng bộ":a.optInt("phuc_than_remaining")+" lượt"),12,Color.rgb(150,200,255)));}

        skill.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int pos,long id){combatDraftSkill[slot][currentEntity]=skillIds.get(Math.max(0,pos));}public void onNothingSelected(AdapterView<?> p){}});mob.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int pos,long id){combatDraftMob[slot][currentEntity]=pos+1;}public void onNothingSelected(AdapterView<?> p){}});hpBar.setOnSeekBarChangeListener(draftSeek(hpLabel,who+" dùng HP khi máu dưới ","%",slot,currentEntity,true));spBar.setOnSeekBarChangeListener(draftSeek(spLabel,who+" dùng SP khi mana dưới ","%",slot,currentEntity,false));phucBox.setOnCheckedChangeListener((b,c)->combatDraftFlags[slot][0]=c);daiBox.setOnCheckedChangeListener((b,c)->combatDraftFlags[slot][1]=c);hoPhuBox.setOnCheckedChangeListener((b,c)->combatDraftFlags[slot][2]=c);
        final String profileKey="combat_profiles_"+user,selectedKey="combat_profile_selected_"+user;JSONArray loaded;try{loaded=new JSONArray(savedAccounts.getString(profileKey,"[]"));}catch(Exception e){loaded=new JSONArray();}final JSONArray profiles=loaded;
        List<String> names=new ArrayList<>();names.add("Mặc định / không chọn");for(int i=0;i<profiles.length();i++){JSONObject p=profiles.optJSONObject(i);names.add(p==null?"Cấu hình "+(i+1):p.optString("name","Cấu hình "+(i+1)));}body.addView(txt("Cấu hình chung • Tướng + 4 pet",13,Color.WHITE));Spinner profile=new Spinner(getContext());profile.setAdapter(readableAdapter(names));int profilePos=names.indexOf(savedAccounts.getString(selectedKey,""));profile.setSelection(Math.max(0,profilePos));body.addView(profile,new LayoutParams(-1,dp(52)));EditText profileName=new EditText(getContext());profileName.setHint("Tên cấu hình");profileName.setHintTextColor(Color.rgb(145,163,186));profileName.setTextColor(Color.WHITE);profileName.setText(combatDraftProfileName[slot]);profileName.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){combatDraftProfileName[slot]=s.toString();}public void afterTextChanged(android.text.Editable e){}});body.addView(profileName,new LayoutParams(-1,dp(50)));
        LinearLayout profileButtons=new LinearLayout(getContext());Button load=btn("TẢI CẤU HÌNH"),saveProfile=btn("LƯU / SỬA");profileButtons.addView(load,new LayoutParams(0,dp(52),1));profileButtons.addView(saveProfile,new LayoutParams(0,dp(52),1));body.addView(profileButtons);Button delete=btn("🗑 XÓA CẤU HÌNH ĐÃ CHỌN");body.addView(delete,new LayoutParams(-1,dp(50)));
        load.setOnClickListener(v->{int index=profile.getSelectedItemPosition()-1;if(index<0){savedAccounts.edit().remove(selectedKey).apply();combatDraftProfileName[slot]="";profileName.setText("");return;}JSONObject p=profiles.optJSONObject(index);if(p==null)return;restoreCombatDraft(slot,p.optJSONObject("draft"));combatDraftProfileName[slot]=p.optString("name");savedAccounts.edit().putString(selectedKey,p.optString("name")).apply();renderBody();});if(profilePos>0&&!savedAccounts.getString(selectedKey,"").equals(combatDraftProfileName[slot]))profile.post(load::performClick);
        saveProfile.setOnClickListener(v->{String name=profileName.getText().toString().trim();if(name.isEmpty()){Toast.makeText(getContext(),"Hãy đặt tên cấu hình",Toast.LENGTH_SHORT).show();return;}try{JSONObject p=new JSONObject();p.put("name",name);p.put("draft",combatDraftJson(slot));int index=profile.getSelectedItemPosition()-1;if(index<0)for(int i=0;i<profiles.length();i++){JSONObject old=profiles.optJSONObject(i);if(old!=null&&name.equalsIgnoreCase(old.optString("name"))){index=i;break;}}if(index>=0)profiles.put(index,p);else profiles.put(p);combatDraftProfileName[slot]=name;savedAccounts.edit().putString(profileKey,profiles.toString()).putString(selectedKey,name).apply();Toast.makeText(getContext(),"Đã lưu toàn bộ Tướng + 4 pet: "+name,Toast.LENGTH_SHORT).show();combatEditorLocked=false;renderBody();}catch(Exception e){Toast.makeText(getContext(),"Không lưu được cấu hình",Toast.LENGTH_LONG).show();}});
        delete.setOnClickListener(v->{int index=profile.getSelectedItemPosition()-1;if(index<0){Toast.makeText(getContext(),"Hãy chọn cấu hình cần xóa",Toast.LENGTH_SHORT).show();return;}JSONObject p=profiles.optJSONObject(index);String name=p==null?"cấu hình":p.optString("name","cấu hình");new AlertDialog.Builder(getContext()).setTitle("Xóa cấu hình?").setMessage(name).setNegativeButton("HỦY",null).setPositiveButton("XÓA",(d,w)->{profiles.remove(index);savedAccounts.edit().putString(profileKey,profiles.toString()).remove(selectedKey).apply();combatEditorLocked=false;renderBody();}).show();});
        Button apply=btn("✓ ÁP DỤNG CHO "+(currentEntity==0?"TƯỚNG":entityName.toUpperCase(Locale.ROOT)));apply.setOnClickListener(v->{int selectedSkill=skillIds.get(Math.max(0,skill.getSelectedItemPosition())),selectedMob=mob.getSelectedItemPosition()+1;combatDraftSkill[slot][currentEntity]=selectedSkill;combatDraftMob[slot][currentEntity]=selectedMob;combatDraftHp[slot][currentEntity]=hpBar.getProgress();combatDraftSp[slot][currentEntity]=spBar.getProgress();int sendCharSkill=combatDraftSkill[slot][0],sendPetSkill=currentEntity==0?0:selectedSkill;int sendCharMob=combatDraftMob[slot][0],sendPetMob=currentEntity==0?4:selectedMob;int sendCharHp=combatDraftHp[slot][0],sendCharSp=combatDraftSp[slot][0],sendPetHp=currentEntity==0?70:combatDraftHp[slot][currentEntity],sendPetSp=currentEntity==0?70:combatDraftSp[slot][currentEntity];boolean sendPhuc=combatDraftFlags[slot][0],sendDai=combatDraftFlags[slot][1],sendHoPhu=combatDraftFlags[slot][2];apply.setEnabled(false);apply.setText("✓ ĐÃ GỬI CẤU HÌNH");if(actionListener!=null)actionListener.onCombatSettings(slot,user,currentEntity==0?0:entityId,sendCharSkill,sendPetSkill,sendCharHp,sendCharSp,sendPhuc,sendDai,sendCharMob,sendPetMob,sendPetHp,sendPetSp,sendHoPhu,false);});LayoutParams applyLp=new LayoutParams(-1,dp(60));applyLp.setMargins(0,dp(8),0,0);body.addView(apply,applyLp);
        body.addView(txt(currentEntity==0?"Tab Tướng chỉ lưu skill, HP/SP và vật phẩm hỗ trợ của tướng.":"Tab này chỉ lưu skill, rule và HP/SP của "+entityName+"; không thay đổi cấu hình các pet khác.",12,Color.rgb(155,175,200)));
    }
    private SeekBar.OnSeekBarChangeListener draftSeek(TextView label,String prefix,String suffix,int slot,int entity,boolean hp){return new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int value,boolean fromUser){label.setText(prefix+value+suffix);if(hp)combatDraftHp[slot][entity]=value;else combatDraftSp[slot][entity]=value;}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}};}
    private JSONObject combatDraftJson(int slot){JSONObject root=new JSONObject();try{JSONArray entities=new JSONArray();for(int i=0;i<5;i++){JSONObject e=new JSONObject();e.put("skill",combatDraftSkill[slot][i]);e.put("mob",combatDraftMob[slot][i]);e.put("hp",combatDraftHp[slot][i]);e.put("sp",combatDraftSp[slot][i]);entities.put(e);}root.put("entities",entities);root.put("phuc",combatDraftFlags[slot][0]);root.put("dai_phuc",combatDraftFlags[slot][1]);root.put("ho_phu",combatDraftFlags[slot][2]);}catch(Exception ignored){}return root;}
    private void restoreCombatDraft(int slot,JSONObject root){if(root==null)return;JSONArray entities=root.optJSONArray("entities");if(entities!=null)for(int i=0;i<Math.min(5,entities.length());i++){JSONObject e=entities.optJSONObject(i);if(e==null)continue;combatDraftSkill[slot][i]=e.optInt("skill",combatDraftSkill[slot][i]);combatDraftMob[slot][i]=Math.max(1,e.optInt("mob",combatDraftMob[slot][i]));combatDraftHp[slot][i]=e.optInt("hp",combatDraftHp[slot][i]);combatDraftSp[slot][i]=e.optInt("sp",combatDraftSp[slot][i]);}combatDraftFlags[slot][0]=root.optBoolean("phuc",combatDraftFlags[slot][0]);combatDraftFlags[slot][1]=root.optBoolean("dai_phuc",combatDraftFlags[slot][1]);combatDraftFlags[slot][2]=root.optBoolean("ho_phu",combatDraftFlags[slot][2]);}
    private void styleEntityTab(Button button,boolean active){button.setTextColor(Color.WHITE);button.setBackgroundTintList(ColorStateList.valueOf(active?Color.rgb(36,125,170):Color.rgb(35,45,58)));}

    private ArrayAdapter<String> readableAdapter(List<String> values){return new ArrayAdapter<String>(getContext(),android.R.layout.simple_spinner_item,values){private TextView style(View v,boolean dropdown){TextView t=(TextView)v;t.setTextColor(Color.WHITE);t.setTextSize(14);t.setPadding(dp(12),dp(10),dp(12),dp(10));t.setBackgroundColor(dropdown?Color.rgb(27,42,62):Color.rgb(20,35,55));return t;}@Override public View getView(int position,View convertView,ViewGroup parent){return style(super.getView(position,convertView,parent),false);}@Override public View getDropDownView(int position,View convertView,ViewGroup parent){return style(super.getDropDownView(position,convertView,parent),true);}};}
    private SeekBar.OnSeekBarChangeListener seek(TextView label,String prefix,String suffix){return new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int value,boolean fromUser){label.setText(prefix+value+suffix);}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}};}
    private void renderInfo(JSONObject a){
        long hp=a.optLong("hp"),hm=a.optLong("hp_max"),sp=a.optLong("sp"),sm=a.optLong("sp_max");
        long php=a.optLong("pet_hp"),phm=a.optLong("pet_hp_max"),psp=a.optLong("pet_sp"),psm=a.optLong("pet_sp_max");
        String charName=a.optString("name",a.optString("user","Nhân vật"));
        String petName=a.optString("pet_name","Pet chưa xác định");
        gameStatusPanel("👤 "+charName,"Cấp "+nullable(a,"level")+(a.optBoolean("leader")?"  •  LEADER":""),hp,hm,sp,sm,a.optLong("exp_in_level"),a.optLong("exp_level_total"),a.has("exp_in_level")&&!a.isNull("exp_in_level"),a.has("exp_level_total")&&!a.isNull("exp_level_total"));
        gameStatusPanel("🐾 "+petName,"Cấp "+nullable(a,"pet_level"),php,phm,psp,psm,a.optLong("pet_exp_current"),a.optLong("pet_exp_level_total"),a.has("pet_exp_current")&&!a.isNull("pet_exp_current"),a.has("pet_exp_level_total")&&!a.isNull("pet_exp_level_total"));
        LinearLayout money=new LinearLayout(getContext());money.setOrientation(HORIZONTAL);money.addView(stat("VÀNG",nullable(a,"gold"),Color.rgb(255,205,75)),new LayoutParams(0,dp(88),1));money.addView(stat("TIỀN ĐỒNG",nullable(a,"money"),Color.rgb(235,165,80)),new LayoutParams(0,dp(88),1));body.addView(money);
        renderExpRate(a,charName,petName);
        renderDailyProgress(a);
        renderDeathSettings(a);
        renderAutoButtons(a);
        Button furnace=btn("XEM LÒ THƯỜNG & LÒ HOÀNG KIM");furnace.setEnabled(a.optBoolean("online"));furnace.setOnClickListener(v->{sectionMode=7;renderBody();accountAction(a,"furnace_scan",new JSONObject());});body.addView(furnace,new LayoutParams(-1,dp(56)));
        TextView note=txt("EXP pet lấy từ packet server và bảng TrueBot cấp 0–201. Pet chuyển sinh ID 45000–45999 tự dùng bảng EXP riêng.",12,Color.rgb(155,175,200));note.setPadding(0,dp(10),0,0);body.addView(note);
    }
    private void renderAutoButtons(JSONObject a){
        final int accountSlot=selected;
        final String user=a.optString("user",configuredUser(selected));
        boolean online=a.optBoolean("online");
        boolean autoOn=a.optBoolean("auto_battle_enabled",false);
        boolean pursuitOn=a.optBoolean("auto_pursuit_enabled",false);
        body.addView(txt("⚔  CÔNG TẮC BATTLE & DI CHUYỂN (mỗi acc riêng)",16,gold));
        LinearLayout row=new LinearLayout(getContext());row.setOrientation(HORIZONTAL);
        Button battle=btn("⚔  AUTO BATTLE"),pursuit=btn("🏹  AUTO TRUY KÍCH");
        battle.setEnabled(online);pursuit.setEnabled(online);
        tint(battle,autoOn);tint(pursuit,pursuitOn);
        battle.setOnClickListener(v->sendAutoMode(accountSlot,user,"battle"));
        pursuit.setOnClickListener(v->sendAutoMode(accountSlot,user,"pursuit"));
        row.addView(battle,new LayoutParams(0,dp(58),1));row.addView(pursuit,new LayoutParams(0,dp(58),1));
        body.addView(row,new LayoutParams(-1,-2));
        body.addView(txt("AUTO BATTLE: "+(autoOn?"BẬT":"TẮT")+" — tự đánh bằng setting Pet & Skill.\nAUTO TRUY KÍCH: "+(pursuitOn?"BẬT":"TẮT")+" — chỉ di chuyển hình số 8, không tự đánh. Bấm lại cùng nút để tắt.",12,Color.rgb(155,175,200)));
    }
    private void tint(Button b,boolean on){
        int[][] states=new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}};
        b.setBackgroundTintList(new ColorStateList(states,new int[]{Color.rgb(38,43,52),on?Color.rgb(230,150,40):Color.rgb(58,70,88)}));
    }
    private void sendAutoMode(int slot,String user,String mode){
        if(actionListener!=null)actionListener.onAutoMode(slot,user,mode);
    }
    private void renderDeathSettings(JSONObject a){
        final String user=a.optString("user",configuredUser(selected));
        JSONObject death=a.optJSONObject("death_return");
        final CheckBox character=new CheckBox(getContext()),pet=new CheckBox(getContext());
        character.setText("Tướng chết về thành");pet.setText("Pet chết về thành");
        character.setTextColor(Color.WHITE);pet.setTextColor(Color.WHITE);
        character.setChecked(savedAccounts.getBoolean("death_char_"+user,death==null||death.optBoolean("character",true)));
        pet.setChecked(savedAccounts.getBoolean("death_pet_"+user,death==null||death.optBoolean("pet",true)));
        body.addView(character);body.addView(pet);
        CompoundButton.OnCheckedChangeListener save=(button,checked)->{
            final boolean ch=character.isChecked(),pe=pet.isChecked();
            savedAccounts.edit().putBoolean("death_char_"+user,ch).putBoolean("death_pet_"+user,pe).apply();
            new Thread(()->{try{
                String result=com.chaquo.python.Python.getInstance().getModule("agent_bridge").callAttr("apply_death_settings_json",user,ch,pe).toString();
                JSONObject response=new JSONObject(result);
                if(!response.optBoolean("ok"))post(()->Toast.makeText(getContext(),response.optString("message","Không lưu được"),Toast.LENGTH_LONG).show());
            }catch(Exception e){post(()->Toast.makeText(getContext(),"Lưu chết về thành thất bại: "+e.getMessage(),Toast.LENGTH_LONG).show());}},"save-death-settings").start();
        };
        character.setOnCheckedChangeListener(save);pet.setOnCheckedChangeListener(save);
    }
    private void renderExpRate(JSONObject a,String charName,String petName){
        JSONObject r=a.optJSONObject("exp_rate");if(r==null)r=new JSONObject();
        LinearLayout box=new LinearLayout(getContext());box.setOrientation(VERTICAL);
        box.setPadding(dp(12),dp(12),dp(12),dp(12));box.setBackgroundColor(Color.rgb(13,38,48));
        TextView title=txt("⏱ HIỆU SUẤT FARM • "+charName,15,Color.rgb(105,225,180));
        title.setTypeface(Typeface.DEFAULT_BOLD);box.addView(title);
        int battles=r.optInt("battles");long elapsed=r.optLong("session_seconds");
        double bph=r.optDouble("battles_per_hour",0);
        box.addView(txt("Số trận/giờ: "+String.format(Locale.US,"%.1f",bph)+(elapsed<60?"  •  Đang đo, chưa đủ 1 phút":""),14,Color.WHITE));
        box.addView(txt("👤 "+charName+": "+num(r.optLong("char_exp_per_hour"))+" EXP/giờ",14,Color.rgb(115,225,140)));
        box.addView(txt("🐾 "+petName+": "+num(r.optLong("pet_exp_per_hour"))+" EXP/giờ",14,Color.rgb(105,185,255)));
        if(battles>0)box.addView(txt("Trận gần nhất: "+String.format(Locale.US,"%.1f",r.optDouble("last_battle_seconds",0))+" giây",13,Color.WHITE));
        box.addView(txt("Riêng account này: "+battles+" trận hoàn tất / "+formatDuration(elapsed)+" • gồm thời gian nghỉ giữa trận",12,Color.rgb(160,185,205)));
        box.addView(txt("EXP đã nhận: Tướng +"+num(r.optLong("char_exp_total"))+" • Pet +"+num(r.optLong("pet_exp_total")),12,Color.rgb(160,185,205)));
        if(r.optLong("char_exp_total")==0)box.addView(txt("Chưa ghi nhận EXP tướng tăng từ server trong phiên này.",12,Color.rgb(255,185,90)));
        LayoutParams lp=new LayoutParams(-1,-2);lp.setMargins(0,dp(6),0,dp(8));body.addView(box,lp);
    }
    private String formatDuration(long seconds){long h=seconds/3600,m=(seconds%3600)/60,s=seconds%60;return h>0?h+"g "+m+"p":m>0?m+"p "+s+"g":s+" giây";}
    private void gameStatusPanel(String name,String sub,long hp,long hpMax,long sp,long spMax,long exp,long expMax,boolean hasExp,boolean hasExpMax){LinearLayout box=new LinearLayout(getContext());box.setOrientation(VERTICAL);box.setPadding(dp(12),dp(11),dp(12),dp(12));box.setBackgroundColor(Color.rgb(14,31,51));TextView title=txt(name,17,Color.WHITE);title.setTypeface(Typeface.DEFAULT_BOLD);box.addView(title);box.addView(txt(sub,12,Color.rgb(175,200,225)));gameBar(box,"HP",hp,hpMax,true,Color.rgb(225,53,64));gameBar(box,"SP",sp,spMax,true,Color.rgb(44,139,232));gameBar(box,"EXP",exp,expMax,hasExp&&hasExpMax,Color.rgb(77,196,64));LayoutParams lp=new LayoutParams(-1,-2);lp.setMargins(0,dp(6),0,dp(8));body.addView(box,lp);}
    private void gameBar(LinearLayout box,String label,long value,long max,boolean known,int color){
        boolean available=known&&max>0;
        double ratio=available?Math.max(0,Math.min(1,(double)value/(double)max)):0;
        LinearLayout header=new LinearLayout(getContext());header.setGravity(Gravity.CENTER_VERTICAL);
        TextView key=txt(label,12,Color.WHITE);key.setTypeface(Typeface.DEFAULT_BOLD);
        header.addView(key,new LayoutParams(0,-2,1));
        String valueText=available?num(value)+" / "+num(max)+"   "+(int)(ratio*100)+"%":"Chưa có dữ liệu";
        TextView amount=txt(valueText,12,Color.WHITE);amount.setGravity(Gravity.RIGHT);
        header.addView(amount,new LayoutParams(-2,-2));box.addView(header,new LayoutParams(-1,-2));
        ProgressBar bar=new ProgressBar(getContext(),null,android.R.attr.progressBarStyleHorizontal);
        bar.setIndeterminate(false);bar.setMax(1000);bar.setProgress((int)Math.round(ratio*1000));
        bar.setProgressTintList(ColorStateList.valueOf(color));
        bar.setProgressBackgroundTintList(ColorStateList.valueOf(Color.rgb(48,57,70)));
        bar.setPadding(0,0,0,0);
        LayoutParams barParams=new LayoutParams(-1,dp(20));barParams.setMargins(0,dp(3),0,dp(8));
        box.addView(bar,barParams);
    }
    private void renderDailyProgress(JSONObject a){LinearLayout box=new LinearLayout(getContext());box.setOrientation(VERTICAL);box.setPadding(dp(12),dp(12),dp(12),dp(12));box.setBackgroundColor(Color.rgb(13,31,51));TextView title=txt("📅 TIẾN ĐỘ HOẠT ĐỘNG HÔM NAY",15,gold);title.setTypeface(Typeface.DEFAULT_BOLD);box.addView(title);box.addView(txt(progressLine("Boss quân đoàn",a,"legion_boss_current","legion_boss_max"),14,Color.WHITE));box.addView(txt(progressLine("Boss thế giới",a,"world_boss_current","world_boss_max"),14,Color.WHITE));box.addView(txt(remainingLine("Khiêu Chiến Đậu Đậu • Phụ bản đơn",a,"solo_dungeon_remaining"),14,Color.WHITE));JSONObject team=a.optJSONObject("team_dungeon_remaining");int[] levels={20,50,80,110};String[] names={"Thảo Phạt Thiên Sư","Ngày Tàn Hoạn Quan","Đại Chiến Lữ Bố","Hỏa Thiêu Bộc Dương"};for(int i=0;i<levels.length;i++){int level=levels[i];String value="Chưa đồng bộ từ server";if(team!=null&&!team.isNull(String.valueOf(level)))value=team.optInt(String.valueOf(level))==0?"Đã đi":"Chưa đi • còn "+team.optInt(String.valueOf(level))+" lượt";box.addView(txt("• "+names[i]+" • Cấp "+level+": "+value,13,Color.rgb(195,215,238)));}if(!a.optBoolean("daily_progress_synced")){TextView wait=txt("ⓘ Server chưa gửi bảng nhiệm vụ 0x18 trong phiên này; Boss quân đoàn vẫn dùng bộ đếm riêng 0x55.",12,Color.rgb(255,185,90));wait.setPadding(0,dp(8),0,0);box.addView(wait);}LayoutParams lp=new LayoutParams(-1,-2);lp.setMargins(0,dp(10),0,dp(4));body.addView(box,lp);}
    private String progressLine(String label,JSONObject a,String current,String max){if(a.isNull(current)||!a.has(current))return "• "+label+": Chưa có dữ liệu server";int used=a.optInt(current),limit=a.optInt(max);return "• "+label+": đã đánh "+used+" / "+(limit>0?limit:"?")+" • còn "+(limit>0?Math.max(0,limit-used):"?");}
    private String remainingLine(String label,JSONObject a,String key){if(a.isNull(key)||!a.has(key))return "• "+label+": Chưa có dữ liệu server";int remaining=a.optInt(key);return "• "+label+": "+(remaining==0?"Đã đi hết lượt":"Chưa đi • còn "+remaining+" lượt");}
    private void bar(String label,int value,int max,int color){body.addView(txt(label+"  "+num(value)+" / "+(max>0?num(max):"—"),13,Color.WHITE));ProgressBar b=new ProgressBar(getContext(),null,android.R.attr.progressBarStyleHorizontal);b.setMax(Math.max(1,max));b.setProgress(Math.min(value,Math.max(1,max)));b.setProgressTintList(ColorStateList.valueOf(color));b.setProgressBackgroundTintList(ColorStateList.valueOf(Color.rgb(45,55,70)));LayoutParams lp=new LayoutParams(-1,dp(24));lp.setMargins(0,dp(5),0,dp(14));body.addView(b,lp);}
    private View stat(String label,String value){return stat(label,value,Color.WHITE);}
    private View stat(String label,String value,int valueColor){LinearLayout box=new LinearLayout(getContext());box.setOrientation(VERTICAL);box.setPadding(dp(12),dp(10),dp(12),dp(8));box.setBackgroundColor(card);box.addView(txt(label,11,Color.rgb(150,175,205)));TextView v=txt(value,18,valueColor);v.setTypeface(Typeface.DEFAULT_BOLD);box.addView(v);return box;}
    private void accountAction(JSONObject account,String action,JSONObject payload){
        if(actionListener!=null)actionListener.onAccountAction(account.optString("user"),action,payload==null?new JSONObject():payload);
    }
    private void renderBag(JSONObject account,JSONObject bag){
        bagItemViews.clear();bagLockViews.clear();bagSpinners.clear();bagRowButtons.clear();bagShownSlots.clear();
        bagRenderedUser=account.optString("user");bagLive=false;bagHeader=null;
        if(bag==null||bag.length()==0){body.addView(txt("Chưa có snapshot rương đồ. Account cần login ít nhất một lần.",14,Color.LTGRAY));return;}
        JSONArray slots=bag.optJSONArray("slots");
        bagLive=bag.optBoolean("live");
        bagHeader=txt("🎒 RƯƠNG ĐỒ  •  "+bag.optInt("used")+"/"+(bag.optInt("cap")>0?bag.optInt("cap"):"—")+" ô  •  "+(bagLive?"LIVE":"CACHE CHỈ XEM"),14,gold);
        body.addView(bagHeader);
        if(slots==null||slots.length()==0){body.addView(txt("Rương trống hoặc chưa nhận được danh sách vật phẩm.",14,Color.LTGRAY));return;}
        List<String> choices=new ArrayList<>();List<Integer> choiceSlots=new ArrayList<>();
        for(int i=0;i<slots.length();i++){JSONObject it=slots.optJSONObject(i);if(it==null)continue;if(!it.optBoolean("combine",true)||it.optBoolean("locked"))continue;choiceSlots.add(it.optInt("slot"));choices.add("Slot "+it.optInt("slot")+" • "+it.optString("name")+" ×"+it.optInt("cnt"));}
        body.addView(txt("HỢP VẬT PHẨM",13,Color.WHITE));LinearLayout compound=new LinearLayout(getContext());
        Spinner first=new Spinner(getContext()),second=new Spinner(getContext());first.setAdapter(readableAdapter(choices));second.setAdapter(readableAdapter(choices));if(choices.size()>1)second.setSelection(1);compound.addView(first,new LayoutParams(0,dp(54),1));compound.addView(second,new LayoutParams(0,dp(54),1));body.addView(compound);
        Button combine=btn("🧪 HỢP 2 VẬT PHẨM ĐÃ CHỌN");combine.setEnabled(bagLive&&choices.size()>0);combine.setOnClickListener(v->{try{int s1=choiceSlots.get(first.getSelectedItemPosition()),s2=choiceSlots.get(second.getSelectedItemPosition());JSONObject q=new JSONObject();q.put("first",s1);q.put("second",s2);markBagActionPending(account.optString("user"),s1);markBagActionPending(account.optString("user"),s2);accountAction(account,"combine",q);}catch(Exception ignored){}});body.addView(combine,new LayoutParams(-1,dp(56)));
        for(int i=0;i<slots.length();i++){JSONObject it=slots.optJSONObject(i);if(it==null)continue;
            final boolean locked=it.optBoolean("locked"),serverLocked=it.optBoolean("server_locked"),usable=it.optBoolean("use"),equipable=it.optBoolean("equip"),dismantle=it.optBoolean("dis");
            final int slot=it.optInt("slot");final String uname=account.optString("user");bagShownSlots.add(slot);
            LinearLayout row=new LinearLayout(getContext());row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(8),dp(9),dp(8),dp(9));row.setBackgroundColor(i%2==0?card:Color.rgb(12,24,41));
            TextView name=txt(bagItemText(it),12,locked?Color.rgb(180,190,205):Color.WHITE);bagItemViews.put(slot,name);row.addView(name,new LayoutParams(0,-2,1));
            List<Button> rowButtons=new ArrayList<>();
            Button lock=btn(serverLocked?"🔒G":(locked?"🔓MỞ":"🔒"));lock.setEnabled(bagLive&&!serverLocked);lock.setOnClickListener(v->{try{JSONObject q=new JSONObject();q.put("slot",slot);q.put("locked",!locked);markBagActionPending(uname,slot);accountAction(account,"toggle_lock",q);}catch(Exception ignored){}});bagLockViews.put(slot,lock);rowButtons.add(lock);row.addView(lock,new LayoutParams(dp(62),dp(48)));
            if(equipable){Button eq=btn("ĐEO");eq.setEnabled(bagLive&&!locked);eq.setOnClickListener(v->{try{JSONObject q=new JSONObject();q.put("slot",slot);markBagActionPending(uname,slot);accountAction(account,"equip",q);}catch(Exception ignored){}});rowButtons.add(eq);row.addView(eq,new LayoutParams(dp(60),dp(48)));}
            else if(usable){Button use=btn("DÙNG");use.setEnabled(bagLive&&!locked);use.setOnClickListener(v->{int count=Math.max(1,it.optInt("cnt",1));EditText qty=new EditText(getContext());qty.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);qty.setText("1");qty.setSelectAllOnFocus(true);new AlertDialog.Builder(getContext()).setTitle("Dùng "+it.optString("name")).setMessage("Nhập số lượng (1–"+Math.min(255,count)+")").setView(qty).setNegativeButton("HỦY",null).setPositiveButton("DÙNG",(dialog,which)->{try{int amount=Math.max(1,Math.min(Math.min(255,count),Integer.parseInt(qty.getText().toString())));JSONObject q=new JSONObject();q.put("slot",slot);q.put("qty",amount);markBagActionPending(uname,slot);accountAction(account,"use_item",q);}catch(Exception e){Toast.makeText(getContext(),"Số lượng không hợp lệ",Toast.LENGTH_SHORT).show();}}).show();});rowButtons.add(use);row.addView(use,new LayoutParams(dp(66),dp(48)));}
            if(dismantle){Button dis=btn("♻");dis.setEnabled(bagLive&&!locked);dis.setOnClickListener(v->new AlertDialog.Builder(getContext()).setTitle("Phân giải vật phẩm?").setMessage(it.optString("name")+" ×"+it.optInt("cnt")).setNegativeButton("HỦY",null).setPositiveButton("PHÂN GIẢI",(d,w)->{try{JSONObject q=new JSONObject();q.put("slot",slot);markBagActionPending(uname,slot);accountAction(account,"decompose",q);}catch(Exception ignored){}}).show());rowButtons.add(dis);row.addView(dis,new LayoutParams(dp(52),dp(48)));}
            Button drop=btn("🗑");drop.setEnabled(bagLive&&!locked);drop.setOnClickListener(v->new AlertDialog.Builder(getContext()).setTitle("Vứt vật phẩm?").setMessage(it.optString("name")+" ×"+it.optInt("cnt")).setNegativeButton("HỦY",null).setPositiveButton("VỨT",(d,w)->{try{JSONObject q=new JSONObject();q.put("slot",slot);q.put("qty",it.optInt("cnt"));markBagActionPending(uname,slot);accountAction(account,"discard",q);}catch(Exception ignored){}}).show());rowButtons.add(drop);row.addView(drop,new LayoutParams(dp(58),dp(48)));
            ProgressBar spin=new ProgressBar(getContext(),null,android.R.attr.progressBarStyleSmall);spin.setIndeterminate(true);spin.setVisibility(GONE);bagSpinners.put(slot,spin);row.addView(spin,new LayoutParams(dp(34),dp(34)));
            bagRowButtons.put(slot,rowButtons);body.addView(row,new LayoutParams(-1,-2));
        }
        applyBagPending();
    }
    private String bagItemText(JSONObject it){return it.optString("name","Item #"+it.optInt("id"))+"\nSlot "+it.optInt("slot")+"  •  ID "+it.optInt("id")+"  •  ×"+num(it.optInt("cnt"));}
    public void markBagActionPending(String user,int slot){
        if(sectionMode!=1||!bagRenderedUser.equals(user))return;
        bagPendingSlots.add(slot);
        ProgressBar sp=bagSpinners.get(slot);if(sp!=null)sp.setVisibility(VISIBLE);
        List<Button> bs=bagRowButtons.get(slot);if(bs!=null)for(Button b:bs)b.setEnabled(false);
    }
    private void applyBagPending(){
        for(Integer s:bagPendingSlots){ProgressBar sp=bagSpinners.get(s);if(sp!=null)sp.setVisibility(VISIBLE);List<Button> bs=bagRowButtons.get(s);if(bs!=null)for(Button b:bs)b.setEnabled(false);}
    }
    public void finishBagAction(String user,JSONObject bag,boolean ok){
        if(sectionMode!=1||!bagRenderedUser.equals(user))return;
        bagPendingSlots.clear();
        for(ProgressBar sp:bagSpinners.values())sp.setVisibility(GONE);
        if(ok&&bag!=null){updateBagLive(user,bag);return;}
        for(List<Button> bs:bagRowButtons.values())for(Button b:bs)b.setEnabled(bagLive);
    }
    public void updateBagLive(String user,JSONObject bag){
        if(sectionMode!=1||bag==null||!user.equals(bagRenderedUser))return;
        JSONArray slots=bag.optJSONArray("slots");
        java.util.LinkedHashSet<Integer> now=new java.util.LinkedHashSet<>();
        if(slots!=null)for(int i=0;i<slots.length();i++){JSONObject it=slots.optJSONObject(i);if(it!=null)now.add(it.optInt("slot"));}
        if(!now.equals(bagShownSlots)){renderBody();applyBagPending();return;}
        bagLive=bag.optBoolean("live");
        if(bagHeader!=null)bagHeader.setText("🎒 RƯƠNG ĐỒ  •  "+bag.optInt("used")+"/"+(bag.optInt("cap")>0?bag.optInt("cap"):"—")+" ô  •  "+(bagLive?"LIVE":"CACHE CHỈ XEM"));
        for(int i=0;i<slots.length();i++){JSONObject it=slots.optJSONObject(i);if(it==null)continue;
            int slot=it.optInt("slot");
            TextView tv=bagItemViews.get(slot);if(tv!=null){tv.setText(bagItemText(it));tv.setTextColor(it.optBoolean("locked")?Color.rgb(180,190,205):Color.WHITE);}
            Button lk=bagLockViews.get(slot);if(lk!=null){boolean serverLocked=it.optBoolean("server_locked"),locked=it.optBoolean("locked");lk.setText(serverLocked?"🔒G":(locked?"🔓MỞ":"🔒"));lk.setEnabled(bagLive&&!serverLocked&&!bagPendingSlots.contains(slot));}
            List<Button> bs=bagRowButtons.get(slot);if(bs!=null){boolean lkd=it.optBoolean("locked"),pend=bagPendingSlots.contains(slot);Button lk2=bagLockViews.get(slot);for(Button b:bs)b.setEnabled(bagLive&&!pend&&(!lkd||b==lk2));}
        }
    }
    private void renderShop(JSONObject a){
        body.addView(txt("🛒 CỬA HÀNG ACCOUNT • "+a.optString("name"),17,gold));JSONObject shop=a.optJSONObject("shop");if(shop==null)shop=new JSONObject();
        shopCard(a,"🧿 Dị Giới Hộ Phù","36  🪙 VÀNG","Đã mua "+nullable(shop,"ho_phu_used")+" / "+shop.optInt("ho_phu_max",3),"buy_ho_phu");
        shopCard(a,"🎒 Túi Triệu Gọi","60.000  🟤 TIỀN ĐỒNG","Đã mua "+nullable(shop,"bao_hop_used")+" / "+shop.optInt("bao_hop_max",1),"buy_bao_hop");
        shopCard(a,"🃏 Rút thẻ tướng","9.000  🟤 TIỀN ĐỒNG","Còn "+shop.optInt("gacha_card_remaining",1)+" lượt","gacha_card");
        shopCard(a,"🐾 Rút thẻ pet","9.000  🟤 TIỀN ĐỒNG","Còn "+shop.optInt("gacha_pet_remaining",1)+" lượt","gacha_pet");
        body.addView(txt("Giá và lượt mua lấy theo protocol/server hiện có. Nút mua bị chặn khi account đang trong trận.",12,Color.rgb(155,175,200)));
    }
    private void shopCard(JSONObject a,String title,String price,String remain,String action){LinearLayout row=new LinearLayout(getContext());row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(12),dp(10),dp(12),dp(10));row.setBackgroundColor(card);LinearLayout info=new LinearLayout(getContext());info.setOrientation(VERTICAL);info.addView(txt(title,15,Color.WHITE));info.addView(txt(price+"  •  "+remain,13,gold));row.addView(info,new LayoutParams(0,-2,1));Button buy=btn("MUA");buy.setOnClickListener(v->accountAction(a,action,new JSONObject()));row.addView(buy,new LayoutParams(dp(92),dp(50)));LayoutParams lp=new LayoutParams(-1,-2);lp.setMargins(0,dp(4),0,dp(4));body.addView(row,lp);}
    private void renderFurnace(JSONObject a){
        body.addView(txt("🔥 CỬA HÀNG LÒ",18,gold));
        LinearLayout storeTabs=new LinearLayout(getContext());storeTabs.setOrientation(HORIZONTAL);
        String[] storeNames={"🔥 LÒ THƯỜNG","✨ LÒ HOÀNG KIM"};
        for(int i=0;i<2;i++){final int value=i;Button tab=btn(storeNames[i]);styleEntityTab(tab,furnaceStoreSelection[selected]==i);tab.setOnClickListener(v->{furnaceStoreSelection[selected]=value;renderBody();});storeTabs.addView(tab,new LayoutParams(0,dp(52),1));}
        body.addView(storeTabs,new LayoutParams(-1,dp(52)));

        LinearLayout categoryTabs=new LinearLayout(getContext());categoryTabs.setOrientation(HORIZONTAL);
        String[] categoryNames={"📜 BÍ CẤP","🛡 TRANG BỊ","🔐 KIM TỎA"};
        for(int i=0;i<3;i++){final int value=i;Button tab=btn(categoryNames[i]);tab.setTextSize(11);styleEntityTab(tab,furnaceCategorySelection[selected]==i);tab.setOnClickListener(v->{furnaceCategorySelection[selected]=value;renderBody();});categoryTabs.addView(tab,new LayoutParams(0,dp(50),1));}
        LayoutParams categoryLp=new LayoutParams(-1,dp(50));categoryLp.setMargins(0,dp(6),0,dp(8));body.addView(categoryTabs,categoryLp);

        JSONObject furnace=a.optJSONObject("furnace");
        if(furnace==null){body.addView(txt("Đang chờ dữ liệu lò từ server…",14,Color.LTGRAY));addFurnaceReload(a);return;}
        JSONObject furnaceTabs=furnace.optJSONObject("tabs");
        if(furnaceTabs==null){body.addView(txt("Lò chưa mở hoặc chưa có mặt hàng.",14,Color.LTGRAY));addFurnaceReload(a);return;}
        int[][] kinds={{1,2,5},{3,4,6}};int kind=kinds[furnaceStoreSelection[selected]][furnaceCategorySelection[selected]];
        JSONArray items=furnaceTabs.optJSONArray(String.valueOf(kind));
        String selectedTitle=storeNames[furnaceStoreSelection[selected]].replace("🔥 ","").replace("✨ ","")+"  •  "+categoryNames[furnaceCategorySelection[selected]].substring(2);
        body.addView(txt(selectedTitle,14,furnaceStoreSelection[selected]==1?Color.rgb(255,205,75):Color.rgb(120,205,255)));
        if(items==null||items.length()==0){body.addView(txt("Nhóm này chưa có mặt hàng hoặc server chưa mở.",13,Color.LTGRAY));addFurnaceReload(a);return;}

        GridLayout grid=new GridLayout(getContext());grid.setColumnCount(4);grid.setUseDefaultMargins(false);
        for(int i=0;i<items.length();i++){
            JSONObject it=items.optJSONObject(i);if(it==null)continue;
            LinearLayout tile=new LinearLayout(getContext());tile.setOrientation(VERTICAL);tile.setGravity(Gravity.CENTER_HORIZONTAL);tile.setPadding(dp(4),dp(7),dp(4),dp(6));
            android.graphics.drawable.GradientDrawable tileBg=new android.graphics.drawable.GradientDrawable();tileBg.setColor(Color.rgb(18,34,55));tileBg.setCornerRadius(dp(10));tileBg.setStroke(dp(1),it.optBoolean("crit")?gold:Color.rgb(42,62,84));tile.setBackground(tileBg);
            TextView name=txt((it.optBoolean("crit")?"✨ ":"")+it.optString("name","Item #"+it.optInt("id")),10,Color.WHITE);name.setGravity(Gravity.CENTER);name.setMaxLines(3);tile.addView(name,new LayoutParams(-1,0,1));
            TextView quantity=txt("×"+num(it.optInt("quant",1)),10,Color.rgb(170,193,218));quantity.setGravity(Gravity.CENTER);tile.addView(quantity,new LayoutParams(-1,dp(20)));
            String price=it.has("price")?num(it.optLong("price"))+" 🔥":"Chưa rõ giá";TextView priceView=txt(price,11,gold);priceView.setTypeface(Typeface.DEFAULT_BOLD);priceView.setGravity(Gravity.CENTER);tile.addView(priceView,new LayoutParams(-1,dp(24)));
            Button buy=btn(it.optBoolean("bought")?"ĐÃ MUA":"MUA");buy.setTextSize(10);buy.setEnabled(!it.optBoolean("bought"));final int selectedKind=kind;buy.setOnClickListener(v->{try{JSONObject q=new JSONObject();q.put("kind",selectedKind);q.put("slot",it.optInt("index"));q.put("item_id",it.optInt("id"));accountAction(a,"furnace_buy",q);}catch(Exception ignored){}});tile.addView(buy,new LayoutParams(-1,dp(42)));
            GridLayout.LayoutParams cell=new GridLayout.LayoutParams();cell.width=0;cell.height=dp(170);cell.columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f);cell.setMargins(dp(3),dp(3),dp(3),dp(3));grid.addView(tile,cell);
        }
        body.addView(grid,new LayoutParams(-1,-2));addFurnaceReload(a);
    }
    private void addFurnaceReload(JSONObject a){Button reload=btn("↻ TẢI LẠI GIÁ & VẬT PHẨM");reload.setOnClickListener(v->accountAction(a,"furnace_scan",new JSONObject()));LayoutParams lp=new LayoutParams(-1,dp(52));lp.setMargins(0,dp(8),0,dp(4));body.addView(reload,lp);}
    private void saveAccount(int slot,String user,String pass){savedAccounts.edit().putBoolean("remember_"+slot,true).putString("user_"+slot,user).putString("pass_"+slot,pass).apply();}
    private void clearSavedAccount(int slot){savedAccounts.edit().remove("remember_"+slot).remove("user_"+slot).remove("pass_"+slot).apply();}
    private String nullable(JSONObject a,String key){if(a.isNull(key)||!a.has(key))return "Chưa có dữ liệu server";Object v=a.opt(key);return v instanceof Number?num(((Number)v).longValue()):String.valueOf(v);}
    private String num(long n){return NumberFormat.getIntegerInstance(new Locale("vi","VN")).format(n);}
    private TextView txt(String s,int size,int color){TextView t=new TextView(getContext());t.setText(s);t.setTextSize(size);t.setTextColor(color);return t;}
    private Button btn(String s){Button b=new Button(getContext());b.setText(s);int active=card;if(s.contains("LOGIN"))active=Color.rgb(35,125,220);else if(s.contains("AUTO BATTLE"))active=Color.rgb(220,125,35);else if(s.contains("OUT"))active=Color.rgb(185,62,72);else if(s.contains("ÁP DỤNG"))active=Color.rgb(38,145,92);else if(s.contains("DỊCH CHUYỂN"))active=Color.rgb(105,78,180);else if(s.contains("PET & SKILL"))active=Color.rgb(42,112,155);int[][] states=new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}};b.setBackgroundTintList(new ColorStateList(states,new int[]{Color.rgb(38,43,52),active}));b.setTextColor(new ColorStateList(states,new int[]{Color.rgb(112,120,132),Color.WHITE}));return b;}
    private int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+.5f);}
}
/* Misplaced draft retained temporarily outside the compiled class.
        CheckBox dgHoPhu=new CheckBox(getContext());dgHoPhu.setText("🧿 Tự ăn Dị Giới Hộ Phù");dgHoPhu.setTextColor(Color.WHITE);dgHoPhu.setChecked(a.optBoolean("use_digioi_ho_phu",false));body.addView(dgHoPhu,new LayoutParams(-1,dp(52)));
        CheckBox autoBaoHop=new CheckBox(getContext());autoBaoHop.setText("🎒 Tự mua Túi Triệu Gọi");autoBaoHop.setTextColor(Color.WHITE);autoBaoHop.setChecked(a.optBoolean("auto_buy_bao_hop",false));body.addView(autoBaoHop,new LayoutParams(-1,dp(52)));
        Button furnace=btn("🔥 XEM LÒ THƯỜNG & LÒ HOÀNG KIM");furnace.setEnabled(a.optBoolean("online"));furnace.setOnClickListener(v->{sectionMode=7;renderBody();accountAction(a,"furnace_scan",new JSONObject());});body.addView(furnace,new LayoutParams(-1,dp(56)));
        final String profileKey="combat_profiles_"+a.optString("user");JSONArray loadedProfiles;try{loadedProfiles=new JSONArray(savedAccounts.getString(profileKey,"[]"));}catch(Exception e){loadedProfiles=new JSONArray();}final JSONArray profiles=loadedProfiles;List<String> profileNames=new ArrayList<>();profileNames.add("Mặc định • không chọn cấu hình");for(int i=0;i<profiles.length();i++)profileNames.add(profiles.optJSONObject(i).optString("name","Cấu hình "+(i+1)));body.addView(txt("Cấu hình đã lưu",13,Color.WHITE));Spinner profileSpinner=new Spinner(getContext());profileSpinner.setAdapter(readableAdapter(profileNames));body.addView(profileSpinner,new LayoutParams(-1,dp(52)));EditText profileName=new EditText(getContext());profileName.setHint("Tên cấu hình mới, ví dụ: Train 4 quái");profileName.setHintTextColor(Color.rgb(145,163,186));profileName.setTextColor(Color.WHITE);body.addView(profileName,new LayoutParams(-1,dp(54)));
        LinearLayout profileActions=new LinearLayout(getContext());Button loadProfile=btn("ÁP DỤNG CẤU HÌNH"),saveProfile=btn("LƯU CẤU HÌNH");profileActions.addView(loadProfile,new LayoutParams(0,dp(54),1));profileActions.addView(saveProfile,new LayoutParams(0,dp(54),1));body.addView(profileActions);
        loadProfile.setOnClickListener(v->{int index=profileSpinner.getSelectedItemPosition()-1;if(index<0){Toast.makeText(getContext(),"Đang dùng thiết lập mặc định",Toast.LENGTH_SHORT).show();return;}JSONObject p=profiles.optJSONObject(index);if(p==null)return;pet.setSelection(Math.max(0,petIds.indexOf(p.optInt("pet_id",0))));charSkill.setSelection(Math.max(0,charIds.indexOf(p.optInt("char_skill",0))));charMob.setSelection(Math.max(0,Math.min(9,p.optInt("char_mob_min",4)-1)));petMob.setSelection(Math.max(0,Math.min(9,p.optInt("pet_mob_min",4)-1)));hpBar.setProgress(p.optInt("hp",70));spBar.setProgress(p.optInt("sp",70));petHpBar.setProgress(p.optInt("pet_hp",70));petSpBar.setProgress(p.optInt("pet_sp",70));phucThan.setChecked(p.optBoolean("phuc"));daiPhucThan.setChecked(p.optBoolean("dai_phuc"));dgHoPhu.setChecked(p.optBoolean("dg_ho_phu"));autoBaoHop.setChecked(p.optBoolean("bao_hop"));petSkill.postDelayed(()->petSkill.setSelection(Math.max(0,petSkillIds.indexOf(p.optInt("pet_skill",0)))),100);});
        saveProfile.setOnClickListener(v->{String name=profileName.getText().toString().trim();if(name.isEmpty()){Toast.makeText(getContext(),"Hãy đặt tên cấu hình",Toast.LENGTH_SHORT).show();return;}try{JSONObject p=new JSONObject();p.put("name",name);p.put("pet_id",petIds.get(Math.max(0,pet.getSelectedItemPosition())));p.put("char_skill",charIds.get(Math.max(0,charSkill.getSelectedItemPosition())));p.put("pet_skill",petSkillIds.get(Math.max(0,petSkill.getSelectedItemPosition())));p.put("char_mob_min",charMob.getSelectedItemPosition()+1);p.put("pet_mob_min",petMob.getSelectedItemPosition()+1);p.put("hp",hpBar.getProgress());p.put("sp",spBar.getProgress());p.put("pet_hp",petHpBar.getProgress());p.put("pet_sp",petSpBar.getProgress());p.put("phuc",phucThan.isChecked());p.put("dai_phuc",daiPhucThan.isChecked());p.put("dg_ho_phu",dgHoPhu.isChecked());p.put("bao_hop",autoBaoHop.isChecked());int existing=-1;for(int i=0;i<profiles.length();i++)if(name.equalsIgnoreCase(profiles.optJSONObject(i).optString("name"))){existing=i;break;}if(existing>=0)profiles.put(existing,p);else profiles.put(p);savedAccounts.edit().putString(profileKey,profiles.toString()).apply();Toast.makeText(getContext(),"Đã lưu cấu hình "+name,Toast.LENGTH_SHORT).show();combatEditorLocked=false;renderBody();}catch(Exception e){Toast.makeText(getContext(),"Không lưu được: "+e.getMessage(),Toast.LENGTH_LONG).show();}}); */
