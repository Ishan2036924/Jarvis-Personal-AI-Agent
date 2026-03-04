#!/usr/bin/env python3
"""Google Calendar tool with conflict detection."""
import os, sys, json, re, fcntl
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CREDS_DIR = os.path.expanduser('~/.openclaw/certs/google')
TOKEN_PATH = os.path.join(CREDS_DIR, 'token.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    with open(TOKEN_PATH + '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def normalize_time(dt_str):
    """Ensure clean ISO format with dynamic EST/EDT offset for conflict checking.
    Uses ZoneInfo to get the correct offset automatically (EST=-05:00, EDT=-04:00).
    """
    from zoneinfo import ZoneInfo
    _raw = datetime.now(ZoneInfo('America/New_York')).strftime('%z')  # '-0500' or '-0400'
    _tz = _raw[:3] + ':' + _raw[3:]  # '-05:00' or '-04:00'
    clean = re.sub(r'[+-]\d{2}:\d{2}$', '', dt_str)
    clean = clean.rstrip('Z')
    if len(clean) == 19:
        return clean + _tz
    elif len(clean) == 16:
        return clean + ':00' + _tz
    elif len(clean) == 10:
        return clean + 'T00:00:00' + _tz
    return clean + _tz

def list_events(time_min=None, time_max=None, max_results=10):
    service = get_service()
    now = datetime.now(timezone.utc)
    if not time_min:
        time_min = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    if not time_max:
        tomorrow = now + timedelta(days=1)
        time_max = tomorrow.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
    # Strip timezone offsets - API needs Z suffix or clean format
    import re
    time_min = re.sub(r'[+-]\d{2}:\d{2}$', 'Z', time_min) if not time_min.endswith('Z') else time_min
    time_max = re.sub(r'[+-]\d{2}:\d{2}$', 'Z', time_max) if not time_max.endswith('Z') else time_max
    results = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max,
                                     maxResults=max_results, singleEvents=True,
                                     orderBy='startTime').execute()
    events = results.get('items', [])
    output = []
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        end = e['end'].get('dateTime', e['end'].get('date'))
        output.append({
            "id": e['id'],
            "summary": e.get('summary', 'No title'),
            "start": start,
            "end": end,
            "location": e.get('location', ''),
            "description": e.get('description', '')[:200],
            "attendees": [a.get('email','') for a in e.get('attendees', [])]
        })
    if not output:
        print(json.dumps({"message": "No events found for this time range."}))
    else:
        print(json.dumps(output, indent=2))

def create_event(summary, start, end, location=None, description=None, attendees=None, force=False):
    service = get_service()
    
    if not force:
        s_norm = normalize_time(start)
        e_norm = normalize_time(end)
        results = service.events().list(calendarId='primary', timeMin=s_norm, timeMax=e_norm,
                                         singleEvents=True, orderBy='startTime').execute()
        conflicts = results.get('items', [])
        if conflicts:
            clist = [{"summary": c.get('summary','No title'), "start": c['start'].get('dateTime', c['start'].get('date'))} for c in conflicts]
            names = ", ".join([f"{c['summary']} at {c['start']}" for c in clist])
            print(json.dumps({
                "status": "CONFLICT_DETECTED",
                "message": f"Cannot create '{summary}' — conflicts with: {names}. Ask Ishan to confirm or pick a different time. Use --force to override.",
                "conflicts": clist
            }))
            return
    
    event = {
        'summary': summary,
        'start': {'dateTime': start, 'timeZone': 'America/New_York'},
        'end': {'dateTime': end, 'timeZone': 'America/New_York'},
    }
    if location:
        event['location'] = location
    if description:
        event['description'] = description
    if attendees:
        event['attendees'] = [{'email': e.strip()} for e in attendees.split(',')]
    result = service.events().insert(calendarId='primary', body=event).execute()
    print(json.dumps({"status": "created", "id": result['id'], "summary": summary, "start": start, "end": end}))

def update_event(event_id, summary=None, start=None, end=None, location=None, description=None):
    service = get_service()
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    if summary:
        event['summary'] = summary
    if start:
        event['start'] = {'dateTime': start, 'timeZone': 'America/New_York'}
    if end:
        event['end'] = {'dateTime': end, 'timeZone': 'America/New_York'}
    if location:
        event['location'] = location
    if description:
        event['description'] = description
    result = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    print(json.dumps({"status": "updated", "id": result['id'], "summary": result.get('summary','')}))

def delete_event(event_id):
    service = get_service()
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    print(json.dumps({"status": "deleted", "id": event_id}))

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if action == 'list':
        time_min = sys.argv[2] if len(sys.argv) > 2 else None
        time_max = sys.argv[3] if len(sys.argv) > 3 else None
        max_results = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        list_events(time_min, time_max, max_results)
    elif action == 'create':
        summary = sys.argv[2]
        start = sys.argv[3]
        end = sys.argv[4]
        location = sys.argv[5] if len(sys.argv) > 5 else None
        description = sys.argv[6] if len(sys.argv) > 6 else None
        attendees = sys.argv[7] if len(sys.argv) > 7 else None
        force = "--force" in sys.argv
        create_event(summary, start, end, location, description, attendees, force)
    elif action == 'update':
        event_id = sys.argv[2]
        summary = sys.argv[3] if len(sys.argv) > 3 else None
        start = sys.argv[4] if len(sys.argv) > 4 else None
        end = sys.argv[5] if len(sys.argv) > 5 else None
        location = sys.argv[6] if len(sys.argv) > 6 else None
        update_event(event_id, summary, start, end, location)
    elif action == 'delete':
        delete_event(sys.argv[2])
    else:
        print("Usage: calendar_tool.py list|create|update|delete ...")
