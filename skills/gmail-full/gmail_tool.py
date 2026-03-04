#!/usr/bin/env python3
"""
Complete Gmail tool for OpenClaw.
Handles: send (plain + HTML), send with attachments, search, read, reply, forward.
"""
import os, sys, json, base64, mimetypes, fcntl
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CREDS_DIR = os.path.expanduser('~/.openclaw/certs/google')
TOKEN_PATH = os.path.join(CREDS_DIR, 'token.json')
SCOPES = ['https://www.googleapis.com/auth/gmail.send',
           'https://www.googleapis.com/auth/gmail.modify']

def _sign(body, html):
    """Append YOUR_NAME's standard signature. Called by send_email() and reply_email()."""
    if html:
        return body + '<br><br>Regards,<br>YOUR_NAME<br>YOUR_EMAIL'
    return body + '\n\nRegards,\nYOUR_NAME\nYOUR_EMAIL'

def get_service():
    with open(TOKEN_PATH + '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def send_email(to, subject, body, attachment_paths=None, cc=None, bcc=None, html=True):
    service = get_service()
    msg = EmailMessage()
    # Auto-detect HTML if body contains tags
    is_html = html or '<p>' in body or '<br>' in body or '<ul>' in body
    body = _sign(body, is_html)
    if is_html:
        msg.set_content(body, subtype='html')
    else:
        msg.set_content(body)
    msg['To'] = to
    msg['Subject'] = subject
    if cc: msg['Cc'] = cc
    if bcc: msg['Bcc'] = bcc
    if attachment_paths:
        for path in attachment_paths.split(','):
            path = path.strip()
            if not os.path.exists(path):
                print(json.dumps({"error": f"File not found: {path}"}))
                return
            ctype, _ = mimetypes.guess_type(path)
            if ctype is None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            with open(path, 'rb') as f:
                msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                                   filename=os.path.basename(path))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(json.dumps({"status": "sent", "messageId": result['id'], "to": to}))

def search_emails(query, max_results=10):
    service = get_service()
    results = service.users().messages().list(userId='me', q=query,
                                               maxResults=max_results).execute()
    messages = results.get('messages', [])
    output = []
    for m in messages[:max_results]:
        msg = service.users().messages().get(userId='me', id=m['id'],
                                              format='metadata',
                                              metadataHeaders=['Subject','From','Date']).execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        output.append({"id": m['id'], "subject": headers.get('Subject',''),
                       "from": headers.get('From',''), "date": headers.get('Date',''),
                       "snippet": msg.get('snippet','')})
    print(json.dumps(output, indent=2))

def read_email(message_id):
    service = get_service()
    msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    headers = {h['name']: h['value'] for h in msg['payload']['headers']}
    body = ""
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
    print(json.dumps({"id": message_id, "subject": headers.get('Subject',''),
                       "from": headers.get('From',''), "body": body[:3000]}))

def reply_email(message_id, body, html=True):
    service = get_service()
    orig = service.users().messages().get(userId='me', id=message_id, format='metadata',
                                          metadataHeaders=['Subject','From','To','Message-ID']).execute()
    headers = {h['name']: h['value'] for h in orig['payload']['headers']}
    msg = EmailMessage()
    # Auto-detect HTML if body contains tags
    is_html = html or '<p>' in body or '<br>' in body or '<ul>' in body
    body = _sign(body, is_html)
    if is_html:
        msg.set_content(body, subtype='html')
    else:
        msg.set_content(body)
    msg['To'] = headers.get('From', '')
    msg['Subject'] = 'Re: ' + headers.get('Subject', '')
    msg['In-Reply-To'] = headers.get('Message-ID', '')
    msg['References'] = headers.get('Message-ID', '')
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me',
        body={'raw': raw, 'threadId': orig['threadId']}).execute()
    print(json.dumps({"status": "replied", "messageId": result['id'], "to": msg['To']}))

def forward_email(message_id, to):
    service = get_service()
    orig = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    headers = {h['name']: h['value'] for h in orig['payload']['headers']}
    body_text = ""
    if 'parts' in orig['payload']:
        for part in orig['payload']['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    elif 'body' in orig['payload'] and 'data' in orig['payload']['body']:
        body_text = base64.urlsafe_b64decode(orig['payload']['body']['data']).decode('utf-8')
    msg = EmailMessage()
    fwd_body = "---------- Forwarded message ----------\n"
    fwd_body += f"From: {headers.get('From','')}\n"
    fwd_body += f"Date: {headers.get('Date','')}\n"
    fwd_body += f"Subject: {headers.get('Subject','')}\n\n"
    fwd_body += body_text
    msg.set_content(fwd_body)
    msg['To'] = to
    msg['Subject'] = 'Fwd: ' + headers.get('Subject', '')
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(json.dumps({"status": "forwarded", "messageId": result['id'], "to": to}))

def download_attachments(message_id, save_dir="/home/YOUR_USERNAME/files"):
    """Download all attachments from an email."""
    os.makedirs(save_dir, exist_ok=True)
    service = get_service()
    msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    parts = msg.get('payload', {}).get('parts', [])
    downloaded = []
    for part in parts:
        filename = part.get('filename', '')
        if not filename:
            continue
        att_id = part['body'].get('attachmentId')
        if att_id:
            att = service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=att_id).execute()
            data = base64.urlsafe_b64decode(att['data'])
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(data)
            downloaded.append(filepath)
    print(json.dumps({"status": "downloaded", "files": downloaded}))

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if action == 'send':
        to, subject, body = sys.argv[2], sys.argv[3], sys.argv[4]
        attachments = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != '--no-html' else None
        html = '--no-html' not in sys.argv  # HTML is default; pass --no-html to force plaintext
        send_email(to, subject, body, attachments, html=html)
    elif action == 'reply':
        reply_email(sys.argv[2], sys.argv[3], '--no-html' not in sys.argv)
    elif action == 'forward':
        forward_email(sys.argv[2], sys.argv[3])
    elif action == 'download':
        download_attachments(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '/home/YOUR_USERNAME/files')
    elif action == 'search':
        search_emails(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif action == 'read':
        read_email(sys.argv[2])
    else:
        print("Usage: gmail_tool.py send|search|read|reply|forward ...")
