import streamlit as st
import pandas as pd
from packages.data_loader import load_data

# 設定頁面資訊
st.set_page_config(
    page_title="萬華國中自動化命題系統",
    page_icon="📚",
    layout="wide"
)

# 讀取 Spreadsheet ID (從 secrets 取得)
# 請在 .streamlit/secrets.toml 中設定 [general] question_bank_id
if "general" in st.secrets and "question_bank_id" in st.secrets["general"]:
    QUESTION_BANK_ID = st.secrets["general"]["question_bank_id"]
else:
    st.warning("未設定 question_bank_id，請檢查 .streamlit/secrets.toml")
    st.stop()


def main():
    st.title("📚 萬華國中自動化命題系統 (Web 旗艦版)")
    st.markdown("---")

    # 側邊欄：功能導航
    with st.sidebar:
        st.header("功能導航")
        page = st.radio("選擇模式", ["管理者篩選挑題 (System 2)", "學生線上練習 (System 1)"])

    if page == "管理者篩選挑題 (System 2)":
        render_system_2()
# 讀取 Digital Footprint ID
# 請在 .streamlit/secrets.toml 中設定 [general] digital_footprint_id
if "general" in st.secrets and "digital_footprint_id" in st.secrets["general"]:
    DIGITAL_FOOTPRINT_ID = st.secrets["general"]["digital_footprint_id"]
else:
    # 為了避免 System 2 使用者受阻，這裡給一個警告但暫不停止，除非進入 System 1
    DIGITAL_FOOTPRINT_ID = None

from packages.generator import generate_b4_word, generate_a4_word
from packages.student_system import StudentSystem
from packages.utils import get_folder_id, get_image_map, download_image_as_bytes
from datetime import datetime

def main():
    st.title("📚 萬華國中自動化命題系統 (Web 旗艦版)")
    st.markdown("---")

    # 側邊欄：功能導航
    with st.sidebar:
        st.header("功能導航")
        page = st.radio("選擇模式", ["學生線上練習 (System 1)", "管理者篩選挑題 (System 2)"])

    if page == "學生線上練習 (System 1)":
        if not DIGITAL_FOOTPRINT_ID:
            st.error("請先在 secrets.toml 設定 digital_footprint_id")
            return
        render_system_1()
    elif page == "管理者篩選挑題 (System 2)":
        render_system_2()

def render_system_1():
    st.subheader("🎓 學生線上練習系統")
    student_sys = StudentSystem(DIGITAL_FOOTPRINT_ID)
    
    # 初始化資料庫區塊 (僅供管理員首次設定)
    with st.expander("⚙️ 系統管理 (資料庫初始化 & 帳號)", expanded=False):
        st.write("### 1. 資料庫結構初始化")
        if st.button("🚀 初始化資料庫結構"):
            with st.spinner("正在檢查並建立資料表..."):
                student_sys.init_schema()
                st.success("資料庫結構檢查/建立完成！")

        st.divider()
        st.write("### 2. 學生帳號管理")
        uploaded_file = st.file_uploader("上傳學生名單 (CSV) - 請使用 UTF-8 編碼", type="csv")
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file, dtype=str)
                st.write("預覽資料：")
                st.dataframe(df.head())
                if st.button("確認匯入"):
                    with st.spinner("正在匯入..."):
                        if student_sys.import_students(df):
                            st.success(f"成功匯入 {len(df)} 筆學生資料！")
            except Exception as e:
                st.error(f"讀取 CSV 失敗: {e}")

from packages.brain import Brain

def render_system_1():
    st.subheader("🎓 學生線上練習系統")
    student_sys = StudentSystem(DIGITAL_FOOTPRINT_ID)
    if "schema_initialized" not in st.session_state:
        try:
            student_sys.init_schema()
            st.session_state["schema_initialized"] = True
        except Exception:
            pass  # Swallow transient SSL/network errors; sheets likely already exist
    
    # 初始化資料庫區塊 (僅供管理員首次設定)
    # ... (Keep existing admin block) ...
    # ---------------------------------------------------------
    # LOGIN LOGIC (Keep as is, but maybe wrapped or just standard)
    # ---------------------------------------------------------
    if "student" not in st.session_state:
        # ... (Login UI) ...
        st.write("### 🔑 學生登入")
        col1, col2 = st.columns([1, 2])
        with col1:
            student_id = st.text_input("請輸入學號")
            login_btn = st.button("登入")
        
        if login_btn and student_id:
            with st.spinner("登入中..."):
                student = student_sys.login(student_id)
                if student:
                    st.session_state["student"] = student
                    
                    # Check Persistence
                    try:
                        session = student_sys.get_active_session(student['Student_ID'])
                    except Exception:
                        session = None
                    
                    if session:
                         try:
                             # Restore Logic - generate UID same as Brain does
                             df_base = load_data(QUESTION_BANK_ID)
                             df_base['UID'] = df_base['年份'].astype(str) + "_" + df_base['來源'].astype(str) + "_" + df_base['題號'].astype(str)
                             
                             uids_str = session.get('Question_UIDs', '')
                             if uids_str:
                                 uids = uids_str.split(',')
                                 restored = df_base[df_base['UID'].isin(uids)].copy()
                                 
                                 if not restored.empty:
                                     # Sort by UIDs order to match original
                                     restored['UID'] = pd.Categorical(restored['UID'], categories=uids, ordered=True)
                                     restored = restored.sort_values('UID').reset_index(drop=True)
                                     
                                     # Init Image Map
                                     folder_id = get_folder_id("Math_Crops")
                                     if folder_id:
                                         st.session_state["quiz_image_map"] = get_image_map(folder_id)
                                     else:
                                         st.session_state["quiz_image_map"] = {}
                                     
                                     st.session_state["quiz_data"] = restored
                                     st.session_state["quiz_active"] = True
                                     st.session_state["quiz_start_time"] = datetime.now()
                                     st.session_state["quiz_index"] = 0
                                     st.session_state["quiz_score"] = 0
                                     st.session_state["quiz_submitted"] = False
                                     st.session_state["quiz_results"] = []
                                     st.session_state["quiz_logged"] = False
                                     st.session_state["current_user_ans"] = None
                                     st.rerun()
                                 else:
                                     pass  # UIDs didn't match, skip restore
                         except Exception:
                             pass  # Restore failed, continue normal login

                    st.rerun()
                else:
                    st.error("找不到此學號，請聯繫老師。")
        return

    # ---------------------------------------------------------
    # LOGGED IN
    # ---------------------------------------------------------
    student = st.session_state["student"]
    

    # Check if in Quiz Mode
    if st.session_state.get("quiz_active"):
        render_quiz_session(student_sys, student)
        return

    # DASHBOARD
    st.write(f"### 👤 學生儀表板 - {student.get('Name')} ({student.get('Student_ID')})")
    
    target_mod = student.get("Target_Module", "N/A")
    
    # Fetch Module Info
    mod_info = student_sys.get_module(target_mod)
    mod_desc = "尚未設定或找不到模組"
    if mod_info:
        mod_desc = (
            f"🎯 **{target_mod}**\n\n"
            f"- **範圍**: {mod_info.get('Filter_Unit', 'ALL')} ({mod_info.get('Filter_Year', 'ALL')})\n"
            f"- **難度**: 易{mod_info.get('Count_Easy')} | 中{mod_info.get('Count_Mid')} | 難{mod_info.get('Count_Hard')}"
        )
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.info(mod_desc)
    with col_info2:
        st.metric("班級", student.get("Class", "N/A"))
        st.metric("狀態", "已登入")
    with col_info3:
        if st.button("登出"):
            del st.session_state["student"]
            if "quiz_active" in st.session_state: del st.session_state["quiz_active"]
            st.rerun()
            
    st.divider()
    
    # 練習模式選擇
    st.subheader("📝 開始練習")
    mode_label = st.radio("選擇模式", ["Phase 1: 廣度隨機練習", "Phase 2: 深度弱點加強"], horizontal=True)
    mode_key = "phase1" if "Phase 1" in mode_label else "phase2"
    
    c_start, c_dl = st.columns([1, 1])
    
    with c_dl:
        if st.button("📄 下載模擬試卷 (A4)", use_container_width=True):
            with st.spinner("正在生成 A4 模擬試卷..."):
                # 1. Load Data
                df_dl = load_data(QUESTION_BANK_ID)
                brain_dl = Brain(df_dl)
            
                # 2. Get Questions (10 for Paper)
                q_paper = brain_dl.get_questions_for_practice(
                    student_id=student['Student_ID'],
                    target_module=target_mod, 
                    history_df=None,
                    mode=mode_key,
                    n=10, 
                    module_config_override=mod_info
                )
                
                if q_paper.empty:
                    st.warning("無題目可生成")
                else:
                    filter_str = f"{target_mod} | {mode_label}"
                    doc_buffer = generate_a4_word(q_paper, filter_str)
                    
                    st.session_state['a4_download'] = doc_buffer
                    st.session_state['a4_name'] = f"練習卷_{datetime.now().strftime('%H%M')}.docx"
                    st.rerun()

    if 'a4_download' in st.session_state:
        st.download_button(
            label="📥 點此下載 Word 檔",
            data=st.session_state['a4_download'],
            file_name=st.session_state['a4_name'],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )
        
    start_clicked = False
    with c_start:
        start_clicked = st.button("🚀 開始測驗 (5題)", use_container_width=True)

    if start_clicked:
        with st.spinner("正在為您挑選題目... (The Brain 運算中)"):
            # 0. Init Resources
            folder_id = get_folder_id("Math_Crops")
            if folder_id:
                st.session_state["quiz_image_map"] = get_image_map(folder_id)
            else:
                st.session_state["quiz_image_map"] = {}

            # 1. Load Data
            df = load_data(QUESTION_BANK_ID)
            
            # 2. Init Brain
            brain = Brain(df)
            
            # 3. Get Questions
            # Pass module config to Brain
            # We need to update Brain to accept this override
            # For now, pass the module name, and let Brain (or logic here) handle.
            # Brain needs the config dict.
            
            questions = brain.get_questions_for_practice(
                student_id=student['Student_ID'],
                target_module=target_mod, # Brain will likely default if not found in its hardcoded map
                history_df=None, # TODO: fetch history
                mode=mode_key,
                n=5,
                module_config_override=mod_info # New parameter to pass dynamic config
            )
            
            if questions.empty:
                st.warning("目前沒有適合的題目，或者題庫已空。")
            else:
                # Save Session for Persistence
                uids = questions['UID'].tolist()
                student_sys.save_session(student['Student_ID'], uids, mode_key, target_mod)

                st.session_state["quiz_data"] = questions
                st.session_state["quiz_active"] = True
                st.session_state["quiz_start_time"] = datetime.now()
                st.session_state["current_answers"] = {}
                st.rerun()

def render_quiz_session(student_sys, student):
    col_h, col_btn = st.columns([3, 1])
    with col_h: 
        st.subheader("📝 線上測驗中")
    with col_btn:
        if st.button("📄 下載本卷", key="btn_gen_a4_quiz", use_container_width=True):
             with st.spinner("生成中..."):
                 q_data = st.session_state["quiz_data"]
                 mod = student.get('Target_Module', 'Self')
                 doc = generate_a4_word(q_data, f"{mod} | 線上練習", include_answer=False)
                 st.session_state['quiz_a4_buffer'] = doc
                 st.rerun()

    if 'quiz_a4_buffer' in st.session_state:
         st.download_button("📥 下載 Word", st.session_state['quiz_a4_buffer'], 
                            f"練習卷_{datetime.now().strftime('%H%M')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="dl_btn_a4_ready")
    
    # Init Session State for Quiz
    if "quiz_index" not in st.session_state:
        st.session_state["quiz_index"] = 0
        st.session_state["quiz_score"] = 0
        st.session_state["quiz_submitted"] = False
        st.session_state["current_user_ans"] = None
        st.session_state["quiz_results"] = [] # Store batch results
        st.session_state["quiz_logged"] = False # Flag for batch write status

    questions = st.session_state["quiz_data"]
    total_q = len(questions)
    current_idx = st.session_state["quiz_index"]
    
    # Progress Bar
    progress = (current_idx) / total_q
    st.progress(progress, text=f"進度: {current_idx}/{total_q} 題")
    
    # Check if finished
    if current_idx >= total_q:
        st.balloons()
        score = st.session_state["quiz_score"]
        st.success(f"🎉 測驗完成！總得分：{score} / {total_q}")
        
        # Batch Write to Sheet
        if not st.session_state["quiz_logged"]:
            with st.spinner("正在儲存您的戰績..."):
                if student_sys.log_footprint(st.session_state["quiz_results"]):
                    # Delete Session
                    student_sys.delete_session(student['Student_ID'])
                    
                    st.session_state["quiz_logged"] = True
                    st.success("✅ 成績已雲端同步！")
                else:
                    st.error("⚠️ 雲端寫入失敗，請截圖此畫面並聯繫老師。")
                    # Optionally allow retry
                    if st.button("重試寫入"):
                        st.rerun()
        else:
             st.info("成績已儲存。")
        
        if st.button("返回儀表板"):
            # Cleanup
            keys = ["quiz_active", "quiz_data", "quiz_index", "quiz_score", "quiz_submitted", "current_user_ans", "quiz_results", "quiz_logged"]
            for k in keys:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
        return

    # Current Question
    row = questions.iloc[current_idx]
    
    # 1. Header (Match Word Generation Format)
    # Format: 【Year Source】 題號：No 單元：Unit 難易度：Diff
    header_text = f"【{row.get('年份')} {row.get('來源')}】  題號：{row.get('題號')}  單元：{row.get('單元')}  難易度：{row.get('難易度')}"
    st.info(header_text)
    
    # 2. Image Display
    image_name = row.get('圖檔名')
    image_map = st.session_state.get("quiz_image_map", {})
    
    if image_name and image_name in image_map:
        # Check cache to avoid re-downloading on rerun
        if st.session_state.get("current_img_index") != current_idx:
             with st.spinner("正在載入題目圖片..."):
                 st.session_state["current_img_bytes"] = download_image_as_bytes(image_map[image_name])
                 st.session_state["current_img_index"] = current_idx
        
        if st.session_state.get("current_img_bytes"):
             st.image(st.session_state["current_img_bytes"], use_container_width=True)
        else:
             st.error(f"圖片下載失敗: {image_name}")
    else:
        st.warning(f"找不到題目圖片: {image_name} (請確認雲端圖檔是否存在)") 
    
    # 3. Options & Interaction
    # Radio needs a unique key per question to reset properly
    user_ans = st.radio(
        "請選擇答案:", 
        ["A", "B", "C", "D"], 
        index=None, 
        key=f"q_radio_{current_idx}",
        horizontal=True,
        disabled=st.session_state["quiz_submitted"]
    )
    
    st.markdown("---")
    
    # Buttons
    if not st.session_state["quiz_submitted"]:
        if st.button("✅ 確認答案", type="primary"):
            if not user_ans:
                st.warning("請先選擇一個答案！")
            else:
                # Check Answer
                correct_ans = str(row.get('答案', '')).strip().upper()
                is_correct = (user_ans == correct_ans)
                
                # Record Result (Batch Store)
                timestamp = datetime.now().isoformat()
                uid = row.get('UID') or f"{row['年份']}_{row['來源']}_{row['題號']}"
                
                result_record = [
                    timestamp,
                    student['Student_ID'],
                    uid,
                    "TRUE" if is_correct else "FALSE",
                    user_ans,
                    "Practice", # Mode
                    student.get('Target_Module', '達B') # Module
                ]
                
                # Append to session list
                st.session_state["quiz_results"].append(result_record)
                
                # Update State
                if is_correct:
                    st.session_state["quiz_score"] += 1
                
                st.session_state["quiz_submitted"] = True
                st.session_state["current_user_ans"] = user_ans 
                st.rerun()
    else:
        # Show Feedback
        correct_ans = str(row.get('答案', '')).strip().upper()
        user_ans = st.session_state["current_user_ans"]
        
        if user_ans == correct_ans:
            st.success(f"🙆‍♂️ 答對了！答案是 {correct_ans}")
        else:
            st.error(f"🙅‍♂️ 答錯了！正確答案是 {correct_ans}")
        
        # Explanation (if any)
        # if '詳解' in row: st.write(row['詳解'])
        
        # Next Button
        btn_text = "下一題 ➡️" if current_idx < total_q - 1 else "查看結果 🏆"
        if st.button(btn_text):
            st.session_state["quiz_index"] += 1
            st.session_state["quiz_submitted"] = False
            st.session_state["current_user_ans"] = None
            st.rerun()
from datetime import datetime

def render_system_2():
    st.subheader("🛠️ 管理者篩選挑題")
    
    # 1. 資料讀取
    with st.spinner("正在讀取題庫資料..."):
        df = load_data(QUESTION_BANK_ID)
    
    if df.empty:
        return

    # 2. 篩選器介面 (Mission 1)
    with st.expander("🔍 篩選條件", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sources = st.multiselect("來源", options=df["來源"].unique())
        with col2:
            years = st.multiselect("年份", options=df["年份"].unique())
        with col3:
            units = st.multiselect("單元", options=df["單元"].unique())
        with col4:
            difficulties = st.multiselect("難度", options=df["難易度"].unique())

    # 套用篩選
    filtered_df = df.copy()
    if sources:
        filtered_df = filtered_df[filtered_df["來源"].isin(sources)]
    if years:
        filtered_df = filtered_df[filtered_df["年份"].isin(years)]
    if units:
        filtered_df = filtered_df[filtered_df["單元"].isin(units)]
    if difficulties:
        filtered_df = filtered_df[filtered_df["難易度"].isin(difficulties)]

    st.markdown(f"**篩選結果：共 {len(filtered_df)} 題**")

    # 3. 結果呈現 (Mission 1)
    # 使用 multiselect column 需要 Streamlit 1.23+
    event = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun", # 啟用選取功能
        selection_mode="multi-row"
    )
    
    selected_indices = event.selection.rows
    selected_df = filtered_df.iloc[selected_indices]

    st.markdown("---")
    
    # 1. 資料讀取
    student_sys = StudentSystem(DIGITAL_FOOTPRINT_ID)
    with st.spinner("正在讀取題庫資料..."):
        df = load_data(QUESTION_BANK_ID)
    
    if df.empty:
        return

    # 2. 篩選器介面 (Mission 1)
# ... (skip lines to match context if possible, or just replace the top block) ...
# Actually, replace_file_content needs exact match. I will split into two edits if needed or just one big block if contiguous. they are not.
# I will make two requests or one if I can.
# Let's do the button first as it's the main issue.

# ...
    
    # 匯出按鈕區塊 & 模組設定
    col_export, col_module = st.columns([1, 1])
    with col_export:
        if st.button("📄 匯出 B4 排版 Word", use_container_width=True):
            if selected_df.empty:
                st.warning("請先勾選題目！")
            else:
                with st.spinner("正在生成 B4 Word 文件 (需下載圖片，請稍候)..."):
                    # 1. 產生標籤字串 (Filter String)
                    filter_parts = []
                    if sources: filter_parts.append(",".join(sources))
                    if years: filter_parts.append(",".join(map(str, years)))
                    if units: filter_parts.append(",".join(units))
                    if difficulties: filter_parts.append(",".join(difficulties))
                    
                    filter_info_str = " | ".join(filter_parts) if filter_parts else "全來源 | 全年份 | 全單元"

                    # 2. 生成 Word
                    doc_buffer = generate_b4_word(selected_df, filter_info_str)
                    
                    if doc_buffer:
                        # 3. 產生下載檔名 (Timestamp)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                        filename = f"萬華國中_命題試卷_{timestamp}.docx"
                        
                        st.success(f"文件生成完畢！ ({filename})")
                        st.download_button(
                            label="📥 下載 Word 檔",
                            data=doc_buffer,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
    
    with col_module:
        if st.button("💾 設定練習模組", use_container_width=True):
            st.session_state["show_module_setter"] = True
    
    # Module Setter Modal (Expander)
    if st.session_state.get("show_module_setter"):
        with st.expander("⚙️ 設定練習模組規則 (New)", expanded=True):
            with st.form("module_form"):
                st.write("### 建立新模組")
                st.info("將當前的篩選條件儲存為學生練習用的模組。")
                
                new_mod_name = st.text_input("模組名稱 (例如: 110年-幾何-強底子)")
                
                # Show Filters
                f_source = ",".join(sources) if sources else "ALL"
                f_year = ",".join(map(str, years)) if years else "ALL"
                f_unit = ",".join(units) if units else "ALL"
                f_diff = ",".join(difficulties) if difficulties else "ALL"
                
                st.text(f"篩選條件: 來源[{f_source}] | 年份[{f_year}] | 單元[{f_unit}] | 難度[{f_diff}]")
                
                st.write("#### 題目難度配比 (總數建議 5 題)")
                c1, c2, c3 = st.columns(3)
                cnt_easy = c1.number_input("易 (Easy)", min_value=0, value=2)
                cnt_mid = c2.number_input("中 (Mid)", min_value=0, value=2)
                cnt_hard = c3.number_input("難 (Hard)", min_value=0, value=1)
                
                if st.form_submit_button("💾 確認儲存模組"):
                    if not new_mod_name:
                        st.error("請輸入模組名稱")
                    else:
                        # Save to Sheet
                        mod_data = [
                            new_mod_name, f_source, f_year, f_unit, f_diff,
                            str(cnt_easy), str(cnt_mid), str(cnt_hard)
                        ]
                        
                        student_sys.init_schema() 
                        if student_sys.save_module(mod_data):
                            st.success(f"模組 [{new_mod_name}] 儲存成功！")
                            st.session_state["show_module_setter"] = False
                            st.rerun()
                        else:
                            st.error("儲存失敗")

if __name__ == "__main__":
    main()
