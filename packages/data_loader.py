import pandas as pd
import streamlit as st
from packages.auth import get_google_services

# 欄位對應定義 (基於你的描述)
COLUMN_NAMES = [
    "來源", "年份", "題號", "單元", "敘述", 
    "答案", "圖檔名", "答對率", "難易度", 
    # 假設後面接 21 個知識點欄位，這裡先暫用 K1-K21 命名，後續可根據實際資料調整
    *[f"K{i}" for i in range(1, 22)] 
]

@st.cache_data(ttl=600)  # 快取 10 分鐘
def load_data(spreadsheet_id, range_col="A:AD"):
    """
    從 Google Sheets 讀取資料並轉為 DataFrame。
    自動偵測第一個工作表名稱。
    """
    sheets_service, _ = get_google_services()
    
    if not sheets_service:
        return pd.DataFrame()

    try:
        # 1. 取得試算表 Metadata 以獲取正確的工作表名稱
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        first_sheet_title = spreadsheet['sheets'][0]['properties']['title']
        
        # 2. 組裝 Range (例如: "會考題庫!A:AD")
        range_name = f"'{first_sheet_title}'!{range_col}"
        
        # 3. 讀取資料
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, 
            range=range_name
        ).execute()
        
        values = result.get('values', [])

        if not values:
            st.warning(f"工作表 '{first_sheet_title}' 查無資料！")
            return pd.DataFrame()

        # 轉為 DataFrame
        # 假設第一列是標題
        df = pd.DataFrame(values[1:], columns=values[0])
        
        return df

    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        # 在開發模式下印出更多資訊幫助除錯
        print(f"DEBUG: load_data failed. ID={spreadsheet_id}, Error={e}")
        return pd.DataFrame()
