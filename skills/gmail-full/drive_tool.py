#!/usr/bin/env python3
"""
Google Drive tool for OpenClaw.
Handles: list, search, read, download, upload, create.
"""
import os, sys, json, io, fcntl
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

CREDS_DIR = os.path.expanduser('~/.openclaw/certs/google')
TOKEN_PATH = os.path.join(CREDS_DIR, 'token.json')
SCOPES = ['https://www.googleapis.com/auth/drive']
DOWNLOAD_DIR = '/home/YOUR_USERNAME/files'

def get_service():
    with open(TOKEN_PATH + '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def list_files(max_results=10):
    service = get_service()
    results = service.files().list(pageSize=max_results,
                                    fields="files(id, name, mimeType, modifiedTime, size)").execute()
    files = results.get('files', [])
    output = []
    for f in files:
        output.append({
            "id": f['id'],
            "name": f['name'],
            "type": f['mimeType'],
            "modified": f.get('modifiedTime', ''),
            "size": f.get('size', 'N/A')
        })
    print(json.dumps(output, indent=2))

def search_files(query, max_results=10):
    service = get_service()
    results = service.files().list(q=f"name contains '{query}' or fullText contains '{query}'",
                                    pageSize=max_results,
                                    fields="files(id, name, mimeType, modifiedTime)").execute()
    files = results.get('files', [])
    output = []
    for f in files:
        output.append({
            "id": f['id'],
            "name": f['name'],
            "type": f['mimeType'],
            "modified": f.get('modifiedTime', '')
        })
    if not output:
        print(json.dumps({"message": "No files found."}))
    else:
        print(json.dumps(output, indent=2))

def read_file(file_id):
    service = get_service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    mime = meta['mimeType']
    if mime == 'application/vnd.google-apps.document':
        content = service.files().export(fileId=file_id, mimeType='text/plain').execute()
        print(json.dumps({"name": meta['name'], "content": content.decode('utf-8')[:5000]}))
    elif mime == 'application/vnd.google-apps.spreadsheet':
        content = service.files().export(fileId=file_id, mimeType='text/csv').execute()
        print(json.dumps({"name": meta['name'], "content": content.decode('utf-8')[:5000]}))
    elif mime.startswith('text/'):
        content = service.files().get_media(fileId=file_id).execute()
        print(json.dumps({"name": meta['name'], "content": content.decode('utf-8')[:5000]}))
    else:
        print(json.dumps({"name": meta['name'], "message": f"Binary file ({mime}). Use download instead."}))

def download_file(file_id):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    service = get_service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    filepath = os.path.join(DOWNLOAD_DIR, meta['name'])
    mime = meta['mimeType']
    if mime.startswith('application/vnd.google-apps'):
        export_mime = 'application/pdf'
        if 'document' in mime:
            filepath += '.pdf'
        elif 'spreadsheet' in mime:
            export_mime = 'text/csv'
            filepath += '.csv'
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)
    with open(filepath, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    print(json.dumps({"status": "downloaded", "path": filepath, "name": meta['name']}))

def upload_file(filepath, folder_id=None):
    service = get_service()
    filename = os.path.basename(filepath)
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = MediaFileUpload(filepath, mimetype=mime_type)
    result = service.files().create(body=file_metadata, media_body=media, fields='id, name, webViewLink').execute()
    print(json.dumps({"status": "uploaded", "id": result['id'], "name": result['name'], "link": result.get('webViewLink', '')}))

def create_doc(name, content=""):
    # Use the same fcntl locking pattern as get_service() to avoid token race conditions
    with open(TOKEN_PATH + '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.document'
    }
    result = service.files().create(body=file_metadata, fields='id, name, webViewLink').execute()
    if content:
        docs_service = build('docs', 'v1', credentials=creds)
        docs_service.documents().batchUpdate(documentId=result['id'], body={
            'requests': [{'insertText': {'location': {'index': 1}, 'text': content}}]
        }).execute()
    print(json.dumps({"status": "created", "id": result['id'], "name": result['name'], "link": result.get('webViewLink', '')}))

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if action == 'list':
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        list_files(max_results)
    elif action == 'search':
        search_files(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif action == 'read':
        read_file(sys.argv[2])
    elif action == 'download':
        download_file(sys.argv[2])
    elif action == 'upload':
        folder_id = sys.argv[3] if len(sys.argv) > 3 else None
        upload_file(sys.argv[2], folder_id)
    elif action == 'create':
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        create_doc(sys.argv[2], content)
    else:
        print("Usage: drive_tool.py list|search|read|download|upload|create ...")
