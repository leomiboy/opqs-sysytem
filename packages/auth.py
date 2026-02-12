import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# 定義需要的權限範圍
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]

@st.cache_resource
def get_google_services():
    """
    初始化並快取 Google API 服務連線。
    優先從 Streamlit secrets 讀取憑證，若無則嘗試讀取本地 credentials.json。
    """
    creds = None
    
    # 嘗試從 Streamlit secrets 讀取
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
    else:
        # Fallback: 嘗試讀取本地檔案 (僅供開發測試)
        try:
            creds = Credentials.from_service_account_file(
                "credentials.json",
                scopes=SCOPES
            )
        except FileNotFoundError:
            st.error("找不到憑證檔案！請設定 .streamlit/secrets.toml 或提供 credentials.json。")
            return None, None

    try:
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return sheets_service, drive_service
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None, None
