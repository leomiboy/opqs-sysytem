import io
import streamlit as st
from googleapiclient.http import MediaIoBaseDownload
from packages.auth import get_google_services

@st.cache_resource(ttl=3600)
def get_folder_id(folder_name="Math_Crops"):
    """
    Get the ID of the folder with the specified name.
    """
    _, drive_service = get_google_services()
    if not drive_service:
        return None
    
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    # Execute query
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if not files:
        st.error(f"找不到資料夾: {folder_name}")
        return None
    
    # Return the first match
    return files[0]['id']

@st.cache_resource(ttl=3600)
def get_image_map(folder_id):
    """
    List all images in the folder and return a map {filename: file_id}.
    This is much faster than searching for each file individually.
    """
    _, drive_service = get_google_services()
    if not drive_service or not folder_id:
        return {}
    
    image_map = {}
    page_token = None
    
    # 支援分頁讀取所有檔案
    while True:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields="nextPageToken, files(id, name)",
            pageToken=page_token
        ).execute()
        
        for file in results.get('files', []):
            image_map[file['name']] = file['id']
            
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    return image_map

def download_image_as_bytes(file_id):
    """
    Download image from Google Drive as bytes.
    """
    _, drive_service = get_google_services()
    if not drive_service:
        return None

    try:
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh
    except Exception as e:
        print(f"Error downloading image {file_id}: {e}")
        return None
