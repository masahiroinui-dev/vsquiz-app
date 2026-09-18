import streamlit as st
from supabase import create_client
import random
import time
import pandas as pd
import os
import base64
import json

# ページ基本設定
st.set_page_config(page_title="VS Quiz App", layout="centered")

# --- カスタムCSS（背景画像 JPG の自動検出・文字・ボタンの視認性向上設定）---
bg_path = None
possible_bg_paths = [
    "asset/bg/bg.jpg",
    "asset/bg/background.jpg",
    "assets/bg/bg.jpg",
    "assets/bg/background.jpg"
]

for path in possible_bg_paths:
    if os.path.exists(path):
        bg_path = path
        break

if bg_path and os.path.exists(bg_path):
    with open(bg_path, "rb") as f:
        bg_bytes = f.read()
    encoded_bg = base64.b64encode(bg_bytes).decode()
    
    st.markdown(
        f"""
        <style>
        /* メイン背景領域への画像適用 */
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_bg}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: #111111;
        }}
        
        /* ヘッダー透明化 */
        [data-testid="stHeader"] {{
            background-color: rgba(0, 0, 0, 0);
        }}

        /* メインコンテンツエリア：半透明白背景＋黒文字 */
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.92);
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.2);
            color: #111111;
        }}

        /* タブレット・ブラウザでのボタン潰れ対策（黒文字黒背景の防止） */
        .stButton > button {{
            background-color: #ffffff !important;
            color: #1a202c !important;
            border: 1px solid #cbd5e0 !important;
            font-weight: bold !important;
        }}
        .stButton > button[kind="primary"] {{
            background-color: #3182ce !important;
            color: #ffffff !important;
            border: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# アイコンファイルと表示名のマッピング定義
ICON_LIST = [
    {"id": 0, "name": "あかべこ", "filename": "あかべこ"},
    {"id": 1, "name": "いぬ", "filename": "いぬ"},
    {"id": 2, "name": "うま", "filename": "うま"},
    {"id": 3, "name": "かえる", "filename": "かえる"},
    {"id": 4, "name": "かっぱ", "filename": "かっぱ"},
    {"id": 5, "name": "きのこ", "filename": "きのこ"},
    {"id": 6, "name": "さる", "filename": "さる"},
    {"id": 7, "name": "ぞんび", "filename": "ぞんび"},
    {"id": 8, "name": "てんぐ", "filename": "てんぐ"},
    {"id": 9, "name": "ぱんだ", "filename": "ぱんだ"},
    {"id": 10, "name": "ぶろっこりー", "filename": "ぶろっこりー"},
    {"id": 11, "name": "らがーまん", "filename": "らがーまん"},
]

def get_icon_path(icon_id):
    """ファイルシステムを自動探索して確実に画像パスを返す関数"""
    if not (0 <= icon_id < len(ICON_LIST)):
        return None
        
    target_name = ICON_LIST[icon_id]["filename"]
    
    search_dirs = [
        "assets/icon",
        "assets/icons",
        "asset/icon",
        "asset/icons"
    ]
    
    for dir_path in search_dirs:
        if os.path.exists(dir_path):
            try:
                files = os.listdir(dir_path)
                for f in files:
                    name_without_ext = os.path.splitext(f)[0]
                    if name_without_ext == target_name:
                        return os.path.join(dir_path, f)
            except Exception:
                continue
    return None

# Supabase接続初期化
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"].rstrip("/")
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def safe_execute(query_builder, retries=3, delay=0.5):
    """ソケットエラー発生時のリトライ"""
    for attempt in range(retries):
        try:
            return query_builder.execute()
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(delay)

st.title("⚡ リアルタイム対戦クイズ")

if "player_id" not in st.session_state:
    st.session_state.player_id = None
if "room_id" not in st.session_state:
    st.session_state.room_id = None
if "submitting" not in st.session_state:
    st.session_state.submitting = False
if "answered_step" not in st.session_state:
    st.session_state.answered_step = -1

# --- サイドバー：途中終了機能 ---
if st.session_state.room_id:
    with st.sidebar:
        st.write(f"🔑 ルームID: **{st.session_state.room_id}**")
        if st.button("⚠️ ゲームを途中終了する", use_container_width=True):
            try:
                if st.session_state.player_id:
                    safe_execute(supabase.table("players").delete().eq("id", st.session_state.player_id))
            except Exception:
                pass
            
            st.session_state.clear()
            st.rerun()

# --- A. プレイヤー登録・ルーム参加画面 ---
if not st.session_state.room_id:
    st.subheader("👤 プレイヤー情報登録")
    player_name = st.text_input("プレイヤー名を入力", max_chars=10)
    
    st.write("キャラアイコンを選択:")
    icon_names = [item["name"] for item in ICON_LIST]
    selected_name = st.selectbox("キャラ選択", icon_names)
    
    selected_icon = next(item for item in ICON_LIST if item["name"] == selected_name)
    icon_id = selected_icon["id"]
    selected_icon_path = get_icon_path(icon_id)
    
    if selected_icon_path:
        st.image(selected_icon_path, width=80, caption=f"選択中: {selected_name}")
    else:
        st.caption("⚠️ 画像ファイルが見つかりません")

    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("新しくルームを作成", type="primary", use_container_width=True, disabled=st.session_state.submitting):
            if player_name:
                st.session_state.submitting = True
                room_id = str(random.randint(1000, 9999))
                
                try:
                    df = pd.read_csv("questions.csv", encoding="utf-8").fillna("")
                except:
                    df = pd.read_csv("questions.csv", encoding="shift-jis").fillna("")
                
                sample_df = df.sample(n=min(10, len(df)))
                sample_qs = sample_df.astype(str).to_dict(orient="records")
                questions_json_str = json.dumps(sample_qs, ensure_ascii=False)
                
                try:
                    safe_execute(supabase.table("rooms").insert({
                        "room_id": room_id,
                        "questions": questions_json_str
                    }))
                    
                    p_res = safe_execute(supabase.table("players").insert({
                        "room_id": room_id,
                        "player_name": player_name,
                        "icon_id": icon_id
                    }))
                    
                    st.session_state.room_id = room_id
                    st.session_state.player_id = p_res.data[0]["id"]
                    st.session_state.is_host = True
                    st.session_state.submitting = False
                    st.rerun()
                except Exception as e:
                    st.session_state.submitting = False
                    st.error(f"❌ 登録エラー: {e}")
            else:
                st.warning("プレイヤー名を入力してください")

    with col2:
        input_room_id = st.text_input("ルームID (4桁)")
        if st.button("ルームに参加", use_container_width=True, disabled=st.session_state.submitting):
            if player_name and input_room_id:
                st.session_state.submitting = True
                try:
                    room_check = safe_execute(supabase.table("rooms").select("*").eq("room_id", input_room_id))
                    if not room_check.data:
                        st.session_state.submitting = False
                        st.error("指定されたルームIDが存在しません。")
                    else:
                        players_res = safe_execute(supabase.table("players").select("*").eq("room_id", input_room_id))
                        players = players_res.data if players_res.data else []
                        
                        if len(players) >= 4:
                            st.session_state.submitting = False
                            st.error("このルームは満員です（最大4名）")
                        else:
                            p_res = safe_execute(supabase.table("players").insert({
                                "room_id": input_room_id,
                                "player_name": player_name,
                                "icon_id": icon_id
                            }))
                            
                            st.session_state.room_id = input_room_id
                            st.session_state.player_id = p_res.data[0]["id"]
                            st.session_state.is_host = False
                            st.session_state.submitting = False
                            st.rerun()
                except Exception as e:
                    st.session_state.submitting = False
                    st.error(f"接続エラー: {e}")

# --- B. ゲーム処理画面 ---
else:
    room_id = st.session_state.room_id
    
    try:
        room_data_res = safe_execute(supabase.table("rooms").select("*").eq("room_id", room_id))
        players_data_res = safe_execute(supabase.table("players").select("*").eq("room_id", room_id))
        room_data = room_data_res.data[0]
        players_data = players_data_res.data
    except Exception as e:
        st.warning("データの取得中に問題が発生しました。再試行しています...")
        time.sleep(1)
        st.rerun()

    questions = json.loads(room_data["questions"])
    my_p = next((p for p in players_data if p["id"] == st.session_state.player_id), None)

    # --- マイステータス枠 ---
    if my_p:
        life_display = "💀 脱落" if my_p.get("is_eliminated", False) else "❤️" * my_p.get("life", 5)
        my_icon_path = get_icon_path(my_p.get("icon_id", 0))
        
        with st.container():
            st.markdown("---")
            c_icon, c_info = st.columns([1, 4])
            with c_icon:
                if my_icon_path:
                    st.image(my_icon_path, width=70)
                else:
                    st.write("👤")
            with c_info:
                st.markdown(f"### 👤 **{my_p['player_name']}** （あなた）")
                st.markdown(f"**ライフ:** <span style='color: #e53e3e; font-size: 1.2rem;'>{life_display}</span>", unsafe_allow_html=True)
            st.markdown("---")

    # B-1. 待機中画面
    if room_data["status"] == "waiting":
        st.info(f"🔑 ルームID: **{room_id}** （参加者待機中 : {len(players_data)}/4 名）")
        
        st.write("【参加中メンバー】")
        p_cols = st.columns(4)
        for idx, p in enumerate(players_data):
            with p_cols[idx]:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=50)
                st.caption(f"**{p['player_name']}**")

        if st.session_state.get("is_host", False):
            if st.button("ゲームスタート！", type="primary", use_container_width=True):
                safe_execute(supabase.table("rooms").update({"status": "countdown"}).eq("room_id", room_id))
                st.rerun()
        else:
            st.write("⏳ ホストがスタートを押すのをお待ちください...")
            time.sleep(2)
            st.rerun()

    # B-1.5. カウントダウン画面
    elif room_data["status"] == "countdown":
        st.markdown("<h2 style='text-align: center;'>まもなくゲームが始まります！</h2>", unsafe_allow_html=True)
        
        countdown_place = st.empty()
        
        for count in range(3, 0, -1):
            countdown_place.markdown(
                f"<h1 style='text-align: center; font-size: 80px; color: #e53e3e;'>{count}</h1>",
                unsafe_allow_html=True
            )
            time.sleep(1)
            
        countdown_place.markdown(
            "<h1 style='text-align: center; font-size: 80px; color: #3182ce;'>START!</h1>",
            unsafe_allow_html=True
        )
        time.sleep(0.5)

        if st.session_state.get("is_host", False):
            safe_execute(supabase.table("rooms").update({"status": "playing"}).eq("room_id", room_id))
            
        st.rerun()

    # B-2. プレイ中画面
    elif room_data["status"] == "playing":
        step = room_data["current_step"]
        
        active_players = [p for p in players_data if not p.get("is_eliminated", False)]
        if step >= 10 or len(active_players) <= 1:
            safe_execute(supabase.table("rooms").update({"status": "finished"}).eq("room_id", room_id))
            st.rerun()

        current_q = questions[step]
        
        st.markdown(f"### 第 {step + 1} 問 / 10")
        
        # 全員の一覧状況
        st.write("【全員の対戦状況】")
        p_cols = st.columns(4)
        for idx, p in enumerate(players_data):
            with p_cols[idx]:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=40)
                
                if p.get("is_eliminated", False):
                    st.caption(f"💀 **{p['player_name']}**\n(脱落)")
                else:
                    hearts = "❤️" * p.get("life", 5)
                    st.caption(f"**{p['player_name']}**\n{hearts}")

        # クイズ問題文
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.95); padding: 18px; border-radius: 10px; border-left: 6px solid #3182ce; margin: 15px 0;">
                <h3 style="color: #111111; margin: 0;">❓ {current_q['question']}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 誰かが正解した場合
        if room_data["winner_name"]:
            st.markdown(
                f"""
                <div style="background-color: #d4edda; color: #155724; padding: 16px; border-radius: 8px; border: 1px solid #c3e6cb; margin-bottom: 12px; font-weight: bold; font-size: 1.1rem;">
                    🎉 <strong>{room_data['winner_name']}</strong> さんが正解しました！
                </div>
                """,
                unsafe_allow_html=True
            )
            st.info(f"💡 **解説**: {current_q.get('explanation', '解説はありません。')}")
            st.write("5秒後に次の問題へ進みます...")
            
            if st.session_state.get("is_host", False):
                time.sleep(5)
                winner_name = room_data["winner_name"]
                for p in players_data:
                    if not p.get("is_eliminated", False):
                        if p["player_name"] == winner_name:
                            new_streak = p.get("streak", 0) + 1
                            new_life = p.get("life", 5)
                            if new_streak >= 2:
                                new_life = min(5, new_life + 1)
                                new_streak = 0
                            
                            safe_execute(supabase.table("players").update({
                                "streak": new_streak,
                                "life": new_life,
                                "score": p["score"] + 1
                            }).eq("id", p["id"]))
                        else:
                            current_life = p.get("life", 5) - 1
                            is_elim = current_life <= 0
                            
                            safe_execute(supabase.table("players").update({
                                "life": max(0, current_life),
                                "streak": 0,
                                "is_eliminated": is_elim
                            }).eq("id", p["id"]))

                safe_execute(supabase.table("rooms").update({
                    "current_step": step + 1,
                    "winner_name": None
                }).eq("room_id", room_id))
            else:
                time.sleep(2)
            st.rerun()

        # 回答入力エリア（明示的な「送信ボタン」必須・1問につき1回のみ回答可能）
        else:
            if my_p and my_p.get("is_eliminated", False):
                st.warning("☠️ あなたは脱落しました。観戦中...")
            elif st.session_state.answered_step == step:
                st.info("⌛ この問題の回答は送信済みです。他プレイヤーの回答または結果をお待ちください。")
            else:
                with st.form(key=f"answer_form_{step}"):
                    user_ans = st.text_input(
                        "回答を入力してください", 
                        autocomplete="off"
                    )
                    submit_button = st.form_submit_button("回答を送信", type="primary", use_container_width=True)
                
                if submit_button and user_ans:
                    # 1問につき1回の回答制限フラグを記録
                    st.session_state.answered_step = step
                    
                    correct_answers = [a.strip().lower() for a in str(current_q["answer"]).split("/")]
                    input_ans = user_ans.strip().lower()
                    
                    if input_ans in correct_answers:
                        safe_execute(supabase.table("rooms").update({"winner_name": my_p["player_name"]}).eq("room_id", room_id))
                        st.rerun()
                    else:
                        current_life = my_p.get("life", 5) - 1
                        is_elim = current_life <= 0
                        
                        safe_execute(supabase.table("players").update({
                            "life": max(0, current_life),
                            "streak": 0,
                            "is_eliminated": is_elim
                        }).eq("id", my_p["id"]))
                        
                        st.error("❌ 不正解！ライフが1減りました。")
                        time.sleep(1)
                        st.rerun()

            time.sleep(2)
            st.rerun()

    # B-3. 最終結果発表画面
    elif room_data["status"] == "finished":
        st.balloons()
        st.header("🏆 最終順位発表 🏆")
        
        sorted_players = sorted(players_data, key=lambda x: (x["score"], x["life"]), reverse=True)
        
        for rank, p in enumerate(sorted_players, 1):
            col_rank, col_icon, col_info = st.columns([1, 1, 3])
            with col_rank:
                st.subheader(f"第 {rank} 位")
            with col_icon:
                icon_path = get_icon_path(p.get("icon_id", 0))
                if icon_path:
                    st.image(icon_path, width=50)
            with col_info:
                status_str = "💀 脱落" if p.get("is_eliminated", False) else f"❤️ 残りライフ: {p['life']}"
                st.write(f"**{p['player_name']}** ({p['score']} 問正解 / {status_str})")
            st.divider()

        if st.button("トップに戻る"):
            st.session_state.clear()
            st.rerun()