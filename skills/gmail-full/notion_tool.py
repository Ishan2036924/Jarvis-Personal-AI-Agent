#!/usr/bin/env python3
"""Notion tool for OpenClaw. All operations."""
import os, sys, json, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

# ── DB / Page ID constants (updated 2026-03-02) ───────────────────────────────
TASKS_TRACKER_DB              = "YOUR_NOTION_DB_ID"
DAILY_ROUTINE_LOG_DB          = "YOUR_NOTION_DB_ID"
BUDGET_TRACKER_DB             = "YOUR_NOTION_DB_ID"
CONTACTS_DB                   = "YOUR_NOTION_DB_ID"
TASKS_DATABASE_PAGE           = "YOUR_NOTION_DB_ID"
PERSONAL_GROWTH_PAGE          = "YOUR_NOTION_DB_ID"
MONTHLY_FINANCIAL_REPORTS_PAGE = "YOUR_NOTION_DB_ID"
MONTHLY_FINANCIAL_GOALS_PAGE   = "YOUR_NOTION_DB_ID"
JOB_TRACKER_DB                 = "YOUR_NOTION_DB_ID"

# ── Auth ──────────────────────────────────────────────────────────────────────
NOTION_KEY = ''
env_path = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('NOTION_API_KEY='):
                NOTION_KEY = line.strip().split('=', 1)[1]
                break
if not NOTION_KEY:
    NOTION_KEY = os.environ.get('NOTION_API_KEY', '')

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def _request(url, data=None, method=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(json.dumps({"error": f"HTTP {e.code}", "details": error_body[:500]}))
        sys.exit(1)

# ── Search ────────────────────────────────────────────────────────────────────
def search(query, max_results=5):
    data = {"query": query, "page_size": max_results}
    result = _request("https://api.notion.com/v1/search", data)
    output = []
    for item in result.get('results', []):
        title = ""
        if item['object'] == 'page':
            for key, val in item.get('properties', {}).items():
                if val.get('type') == 'title':
                    title = ''.join([t.get('plain_text', '') for t in val.get('title', [])])
        elif item['object'] == 'database':
            title = ''.join([t.get('plain_text', '') for t in item.get('title', [])])
        output.append({"id": item['id'], "type": item['object'], "title": title, "url": item.get('url', '')})
    print(json.dumps(output, indent=2))

# ── Read page blocks ──────────────────────────────────────────────────────────
def read_page(page_id):
    result = _request(f"https://api.notion.com/v1/blocks/{page_id}/children")
    blocks = result.get('results', [])
    content = []
    for b in blocks:
        btype = b.get('type', '')
        if btype in ('paragraph', 'heading_1', 'heading_2', 'heading_3',
                     'bulleted_list_item', 'numbered_list_item'):
            texts = b.get(btype, {}).get('rich_text', [])
            content.append(''.join([t.get('plain_text', '') for t in texts]))
    print(json.dumps({"page_id": page_id, "content": content}))

# ── Create page ───────────────────────────────────────────────────────────────
def create_page(parent_id, title, content="", is_database=False):
    if is_database:
        data = {
            "parent": {"database_id": parent_id},
            "properties": {"Name": {"title": [{"text": {"content": title}}]}}
        }
    else:
        data = {
            "parent": {"page_id": parent_id},
            "properties": {"title": [{"text": {"content": title}}]},
            "children": [{"object": "block", "type": "paragraph",
                         "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}}] if content else []
        }
    result = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "created", "id": result['id'], "title": title, "url": result.get('url', '')}))

# ── Create database (generic) ─────────────────────────────────────────────────
def create_database(parent_page_id, title):
    data = {
        "parent": {"page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": {
            "Name": {"title": {}},
            "Status": {"select": {"options": [
                {"name": "To Do", "color": "red"},
                {"name": "In Progress", "color": "yellow"},
                {"name": "Done", "color": "green"}
            ]}},
            "Due Date": {"date": {}},
            "Priority": {"select": {"options": [
                {"name": "High", "color": "red"},
                {"name": "Medium", "color": "yellow"},
                {"name": "Low", "color": "green"}
            ]}},
            "Notes": {"rich_text": {}}
        }
    }
    result = _request("https://api.notion.com/v1/databases", data)
    print(json.dumps({"status": "database_created", "id": result['id'], "title": title, "url": result.get('url', '')}))

# ── Tasks Tracker ─────────────────────────────────────────────────────────────
# Schema: Task name (title), Status (status), Due date (date),
#         Priority (select: High/Medium/Low), Description (rich_text)

_STATUS_MAP = {
    "to do": "Not started",
    "not started": "Not started",
    "todo": "Not started",
    "in progress": "In progress",
    "in-progress": "In progress",
    "inprogress": "In progress",
    "done": "Done",
    "complete": "Done",
    "completed": "Done",
}

def add_task(db_id, name, status="Not started", due_date=None, priority="Medium", description=""):
    normalized_status = _STATUS_MAP.get(status.lower().strip(), status)
    props = {
        "Task name": {"title": [{"text": {"content": name}}]},
        "Status": {"status": {"name": normalized_status}},
        "Priority": {"select": {"name": priority}},
    }
    if due_date:
        props["Due date"] = {"date": {"start": due_date}}
    if description:
        props["Description"] = {"rich_text": [{"text": {"content": description}}]}
    data = {"parent": {"database_id": db_id}, "properties": props}
    result = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "task_added", "id": result['id'], "name": name}))

def update_task(page_id, status=None, priority=None, due_date=None):
    props = {}
    if status:
        normalized = _STATUS_MAP.get(status.lower().strip(), status)
        props["Status"] = {"status": {"name": normalized}}
    if priority:
        props["Priority"] = {"select": {"name": priority}}
    if due_date:
        props["Due date"] = {"date": {"start": due_date}}
    data = {"properties": props}
    req = urllib.request.Request(f"https://api.notion.com/v1/pages/{page_id}",
                                 data=json.dumps(data).encode(), headers=HEADERS, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(json.dumps({"status": "updated", "id": result['id']}))
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}", "details": e.read().decode()[:500]}))

# ── Budget Tracker ────────────────────────────────────────────────────────────
def _current_cycle():
    """Return billing cycle string for today (19th-to-19th). E.g. 'Feb19-Mar19'."""
    now = datetime.now(ZoneInfo('America/New_York'))
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    if now.day >= 19:
        start_m = months[now.month - 1]
        end_m   = months[now.month % 12]
    else:
        start_m = months[(now.month - 2) % 12]
        end_m   = months[now.month - 1]
    return f"{start_m}19-{end_m}19"

def _just_ended_cycle():
    """Return the billing cycle that JUST ENDED on the 19th (for use on rollover day).
    On March 19 → 'Feb19-Mar19'. On April 19 → 'Mar19-Apr19'.
    """
    now = datetime.now(ZoneInfo('America/New_York'))
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    prev_m = months[(now.month - 2) % 12]
    curr_m = months[now.month - 1]
    return f"{prev_m}19-{curr_m}19"

def add_expense(db_id, item, amount, category, payment="Card"):
    today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    cycle = _current_cycle()
    props = {
        "Item": {"title": [{"text": {"content": item}}]},
        "Amount": {"number": float(amount)},
        "Category": {"select": {"name": category}},
        "Payment": {"select": {"name": payment}},
        "Date": {"date": {"start": today}},
        "Cycle": {"rich_text": [{"text": {"content": cycle}}]}
    }
    data = {"parent": {"database_id": db_id}, "properties": props}
    result = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "expense_added", "id": result['id'], "item": item,
                      "amount": amount, "category": category, "cycle": cycle}))

# ── Daily Routine Log ─────────────────────────────────────────────────────────
# Schema (14 user fields + required Name title):
#   Date (date), Wake Time (rich_text), Sleep Time (rich_text),
#   Water (number, liters), Screen Time (number, minutes),
#   No Sugar (checkbox), Morning Workout (checkbox), Gym (checkbox),
#   Journal (checkbox),
#   Morning Routine (multi_select: Skincare/Room Clean/Bath/Meditation/Puja),
#   Night Skincare (checkbox),
#   Breakfast (select: Healthy/Not Healthy/Skipped),
#   Lunch   (select: Healthy/Not Healthy/Skipped),
#   Dinner  (select: Healthy/Not Healthy/Skipped),
#   Notes (rich_text)

_ROUTINE_FIELD_MAP = {
    'wake':              ('Wake Time',        'rich_text'),
    'sleep':             ('Sleep Time',       'rich_text'),
    'water':             ('Water',            'number'),
    'screen':            ('Screen Time',      'number'),
    'screentime':        ('Screen Time',      'number'),
    'screen_time':       ('Screen Time',      'number'),
    'nosugar':           ('No Sugar',         'checkbox'),
    'no_sugar':          ('No Sugar',         'checkbox'),
    'sugar':             ('No Sugar',         'checkbox'),
    'workout':           ('Morning Workout',  'checkbox'),
    'morningworkout':    ('Morning Workout',  'checkbox'),
    'morning_workout':   ('Morning Workout',  'checkbox'),
    'gym':               ('Gym',              'checkbox'),
    'journal':           ('Journal',          'checkbox'),
    'routine':           ('Morning Routine',  'multi_select'),
    'morningroutine':    ('Morning Routine',  'multi_select'),
    'morning_routine':   ('Morning Routine',  'multi_select'),
    'nightskincare':     ('Night Skincare',   'checkbox'),
    'night_skincare':    ('Night Skincare',   'checkbox'),
    'nightskin':         ('Night Skincare',   'checkbox'),
    'breakfast':         ('Breakfast',        'select'),
    'lunch':             ('Lunch',            'select'),
    'dinner':            ('Dinner',           'select'),
    'notes':             ('Notes',            'rich_text'),
}

# Valid Morning Routine options (case-insensitive matching)
_MORNING_ROUTINE_OPTIONS = {"skincare", "room clean", "roomclean", "bath", "meditation", "puja"}
_MORNING_ROUTINE_CANONICAL = {
    "skincare": "Skincare",
    "room clean": "Room Clean",
    "roomclean": "Room Clean",
    "bath": "Bath",
    "meditation": "Meditation",
    "puja": "Puja",
}

def _normalize_routine_option(opt):
    key = opt.strip().lower()
    return _MORNING_ROUTINE_CANONICAL.get(key, opt.strip().title())

def log_health(db_id, *kvpairs):
    """Log daily routine data. Accepts key=value pairs.
    Keys: wake, sleep, water, screen/screentime, nosugar, workout/morningworkout,
          gym, journal, routine/morningroutine, nightskincare, breakfast, lunch,
          dinner, notes
    Morning Routine values: comma-separated from [Skincare, Room Clean, Bath, Meditation, Puja]
    Meal values: Healthy | Not Healthy | Skipped
    """
    today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    date_override = None

    # Parse key=value pairs
    raw = {}
    for kv in kvpairs:
        if '=' not in kv:
            continue
        k, v = kv.split('=', 1)
        key = k.strip().lower().replace('-', '_')
        if key == 'date':
            date_override = v.strip()
        else:
            raw[key] = v.strip()

    entry_date = date_override if date_override else today

    # Find today's existing row
    existing = query_database(db_id, silent=True)
    today_id = None
    for e in existing:
        if e.get('Date') == entry_date:
            today_id = e.get('id')
            break

    # Build properties
    props = {
        "Name":  {"title": [{"text": {"content": entry_date}}]},
        "Date":  {"date": {"start": entry_date}},
    }

    for key, value in raw.items():
        if key not in _ROUTINE_FIELD_MAP:
            continue
        notion_name, ftype = _ROUTINE_FIELD_MAP[key]
        if ftype == 'number':
            try:
                props[notion_name] = {"number": float(value)}
            except ValueError:
                pass
        elif ftype == 'select':
            # Normalize meal values
            v_norm = value.strip().lower()
            if v_norm in ('healthy', 'good'):
                canonical = 'Healthy'
            elif v_norm in ('not healthy', 'nothealthy', 'unhealthy', 'bad', 'junk'):
                canonical = 'Not Healthy'
            elif v_norm in ('skipped', 'skip', 'none', 'no'):
                canonical = 'Skipped'
            else:
                canonical = value.strip().title()
            props[notion_name] = {"select": {"name": canonical}}
        elif ftype == 'multi_select':
            parts = [p.strip() for p in value.split(',') if p.strip()]
            tags = [{"name": _normalize_routine_option(p)} for p in parts]
            props[notion_name] = {"multi_select": tags}
        elif ftype == 'checkbox':
            props[notion_name] = {"checkbox": value.lower() in ('true', 'yes', '1', 'done', 'y')}
        elif ftype == 'rich_text':
            props[notion_name] = {"rich_text": [{"text": {"content": value}}]}

    if today_id:
        # Remove Name/Date from update props (can't patch title of existing row easily)
        update_props = {k: v for k, v in props.items() if k not in ('Name',)}
        try:
            result = _request(f"https://api.notion.com/v1/pages/{today_id}",
                              data={"properties": update_props}, method="PATCH")
            print(json.dumps({"status": "routine_updated", "id": today_id,
                              "date": entry_date, "fields": list(raw.keys())}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    else:
        try:
            result = _request("https://api.notion.com/v1/pages",
                             data={"parent": {"database_id": db_id}, "properties": props})
            print(json.dumps({"status": "routine_created", "id": result.get("id", ""),
                              "date": entry_date, "fields": list(raw.keys())}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))

# Alias for backward compatibility
def add_routine(db_id, *habits):
    """Legacy habit logging — maps old habit names to new Daily Routine Log schema."""
    _OLD_MAP = {
        "exercise":      "workout=yes",
        "gym":           "gym=yes",
        "meditation":    "routine=Meditation",
        "study":         "notes=Studied today",
        "reading":       "notes=Reading done",
        "sleep":         "sleep=Before 12",
    }
    kvpairs = []
    for h in habits:
        mapped = _OLD_MAP.get(h.lower())
        if mapped:
            kvpairs.append(mapped)
    log_health(db_id, *kvpairs)

# ── Monthly Financial Report generator ───────────────────────────────────────
def generate_monthly_report(cycle=None):
    """Query Budget Tracker for a billing cycle, compute totals, create report sub-page.
    cycle: e.g. 'Feb19-Mar19' | 'auto' (uses _just_ended_cycle, for 19th rollover) | None (current cycle).
    """
    if not cycle or cycle == '':
        cycle = _current_cycle()
    elif cycle == 'auto':
        cycle = _just_ended_cycle()

    # Query Budget Tracker filtered by cycle
    filter_data = {
        "filter": {"property": "Cycle", "rich_text": {"equals": cycle}},
        "page_size": 100
    }
    result = _request(f"https://api.notion.com/v1/databases/{BUDGET_TRACKER_DB}/query", filter_data)
    entries = result.get('results', [])

    if not entries:
        print(json.dumps({"error": f"No Budget Tracker entries found for cycle: {cycle}"}))
        return

    total = 0.0
    by_category = {}
    by_payment = {}
    rows = []

    for page in entries:
        p = page.get('properties', {})
        item    = ''.join([t.get('plain_text', '') for t in p.get('Item', {}).get('title', [])])
        amount  = p.get('Amount', {}).get('number', 0) or 0
        cat     = p.get('Category', {}).get('select', {}).get('name', 'Other') if p.get('Category', {}).get('select') else 'Other'
        pay     = p.get('Payment',  {}).get('select', {}).get('name', 'Card')  if p.get('Payment',  {}).get('select') else 'Card'
        date    = p.get('Date', {}).get('date', {}).get('start', '') if p.get('Date', {}).get('date') else ''

        total += amount
        by_category[cat]  = by_category.get(cat, 0) + amount
        by_payment[pay]   = by_payment.get(pay, 0) + amount
        rows.append(f"  • {date}  {item:<35} ${amount:.2f}  [{cat}]  {pay}")

    # Build report text
    lines = [
        f"Monthly Financial Report — Cycle: {cycle}",
        f"Generated: {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M EST')}",
        "",
        f"TOTAL SPENT: ${total:.2f}",
        f"TRANSACTIONS: {len(entries)}",
        "",
        "── By Category ──",
    ]
    for cat, amt in sorted(by_category.items(), key=lambda x: -x[1]):
        pct = (amt / total * 100) if total else 0
        lines.append(f"  {cat:<20} ${amt:.2f}  ({pct:.0f}%)")
    lines += ["", "── By Payment Method ──"]
    for pay, amt in sorted(by_payment.items(), key=lambda x: -x[1]):
        lines.append(f"  {pay:<20} ${amt:.2f}")
    lines += ["", "── All Transactions ──"] + rows

    report_text = '\n'.join(lines)

    # Create sub-page under Monthly Financial Reports
    # Split report into ≤1990-char chunks so Notion's 2000-char block limit is never hit
    page_title = f"Report — {cycle}"
    chunks = [report_text[i:i+1990] for i in range(0, len(report_text), 1990)]
    children = [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"text": {"content": chunk}}]}}
        for chunk in chunks
    ]
    data = {
        "parent": {"page_id": MONTHLY_FINANCIAL_REPORTS_PAGE},
        "properties": {"title": [{"text": {"content": page_title}}]},
        "children": children  # Notion allows up to 100 blocks per create request
    }
    sub = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "report_created", "id": sub['id'], "cycle": cycle,
                      "total": round(total, 2), "transactions": len(entries),
                      "url": sub.get('url', '')}))

# ── Append to page ────────────────────────────────────────────────────────────
def append_to_page(page_id, content):
    data = {
        "children": [{"object": "block", "type": "paragraph",
                      "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}}]
    }
    _request(f"https://api.notion.com/v1/blocks/{page_id}/children", data, method="PATCH")
    print(json.dumps({"status": "appended", "page_id": page_id}))

# ── Query database ────────────────────────────────────────────────────────────
def query_database(db_id, silent=False):
    data = {"page_size": 100}
    result = _request(f"https://api.notion.com/v1/databases/{db_id}/query", data)
    rows = []
    for page in result.get('results', []):
        row = {"id": page['id'], "url": page.get('url', '')}
        for key, val in page.get('properties', {}).items():
            ptype = val.get('type')
            if ptype == 'title':
                row[key] = ''.join([t.get('plain_text', '') for t in val.get('title', [])])
            elif ptype == 'select':
                row[key] = val.get('select', {}).get('name', '') if val.get('select') else ''
            elif ptype == 'status':
                row[key] = val.get('status', {}).get('name', '') if val.get('status') else ''
            elif ptype == 'date':
                row[key] = val.get('date', {}).get('start', '') if val.get('date') else ''
            elif ptype == 'number':
                row[key] = val.get('number', 0)
            elif ptype == 'checkbox':
                row[key] = val.get('checkbox', False)
            elif ptype == 'rich_text':
                row[key] = ''.join([t.get('plain_text', '') for t in val.get('rich_text', [])])
            elif ptype == 'multi_select':
                row[key] = [o.get('name', '') for o in val.get('multi_select', [])]
            elif ptype == 'email':
                row[key] = val.get('email', '')
            elif ptype == 'phone_number':
                row[key] = val.get('phone_number', '')
        rows.append(row)
    if silent:
        return rows
    print(json.dumps(rows, indent=2))

# ── Contacts ──────────────────────────────────────────────────────────────────
def add_contact(db_id, name, email="", phone="", relationship="Other", company="", notes=""):
    props = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Relationship": {"select": {"name": relationship}},
    }
    if email:
        props["Email"] = {"email": email}
    if phone:
        props["Phone"] = {"phone_number": phone}
    if company:
        props["Company"] = {"rich_text": [{"text": {"content": company}}]}
    if notes:
        props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    data = {"parent": {"database_id": db_id}, "properties": props}
    result = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "contact_added", "id": result['id'], "name": name}))

def lookup_contact(db_id, name):
    data = {
        "filter": {"property": "Name", "title": {"contains": name}},
        "page_size": 5
    }
    result = _request(f"https://api.notion.com/v1/databases/{db_id}/query", data)
    contacts = []
    for page in result.get('results', []):
        p = page.get('properties', {})
        contacts.append({
            "name":         ''.join([t.get('plain_text', '') for t in p.get('Name', {}).get('title', [])]),
            "email":        p.get('Email', {}).get('email', ''),
            "phone":        p.get('Phone', {}).get('phone_number', ''),
            "relationship": p.get('Relationship', {}).get('select', {}).get('name', '') if p.get('Relationship', {}).get('select') else '',
            "company":      ''.join([t.get('plain_text', '') for t in p.get('Company', {}).get('rich_text', [])]),
        })
    if contacts:
        print(json.dumps(contacts, indent=2))
    else:
        print(json.dumps({"error": "No contact found", "query": name}))

# ── Job Application Tracking ─────────────────────────────────────────────────
# Valid Source options in the Job Tracker DB
_VALID_JOB_SOURCES = {'Brave', 'Simplify', 'Greenhouse', 'Lever', 'Manual'}

def log_job_application(company, role, source, apply_link="", notes=""):
    """Create a new Job Application entry in the Job Tracker DB."""
    today = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    title = f"{company} — {role}"
    # Map unknown sources to Manual (e.g. LinkedIn)
    mapped_source = source if source in _VALID_JOB_SOURCES else "Manual"
    props = {
        "Title":      {"title": [{"text": {"content": title}}]},
        "Company":    {"rich_text": [{"text": {"content": company}}]},
        "Role":       {"rich_text": [{"text": {"content": role}}]},
        "Source":     {"select": {"name": mapped_source}},
        "Status":     {"select": {"name": "✅ Applied"}},
        "Date Found": {"date": {"start": today}},
    }
    if apply_link:
        props["Link"] = {"url": apply_link}
    if notes:
        props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    data = {"parent": {"database_id": JOB_TRACKER_DB}, "properties": props}
    result = _request("https://api.notion.com/v1/pages", data)
    print(json.dumps({"status": "job_logged", "id": result['id'], "title": title,
                      "company": company, "role": role, "source": mapped_source, "date": today}))

def query_jobs(status_filter=None):
    """Query all Job Application entries from the Job Tracker DB.
    Optionally filter by Status. Returns company, role, status, date, source.
    """
    data = {
        "sorts": [{"property": "Date Found", "direction": "descending"}],
        "page_size": 100
    }
    if status_filter:
        data["filter"] = {"property": "Status", "select": {"equals": status_filter}}
    result = _request(f"https://api.notion.com/v1/databases/{JOB_TRACKER_DB}/query", data)
    rows = []
    for page in result.get('results', []):
        p = page.get('properties', {})
        title = ''.join([t.get('plain_text', '') for t in p.get('Title', {}).get('title', [])])
        company = ''.join([t.get('plain_text', '') for t in p.get('Company', {}).get('rich_text', [])])
        role = ''.join([t.get('plain_text', '') for t in p.get('Role', {}).get('rich_text', [])])
        status = p.get('Status', {}).get('select', {}).get('name', '') if p.get('Status', {}).get('select') else ''
        source = p.get('Source', {}).get('select', {}).get('name', '') if p.get('Source', {}).get('select') else ''
        date_found = p.get('Date Found', {}).get('date', {}).get('start', '') if p.get('Date Found', {}).get('date') else ''
        apply_link = p.get('Link', {}).get('url', '') or ''
        rows.append({
            "id": page['id'],
            "title": title,
            "company": company,
            "role": role,
            "status": status,
            "source": source,
            "date_found": date_found,
            "apply_link": apply_link,
        })
    print(json.dumps(rows, indent=2))

# ── Delete / Archive ──────────────────────────────────────────────────────────
def delete_entry(page_id):
    """Archive (soft-delete) any Notion page by ID."""
    try:
        result = _request(f"https://api.notion.com/v1/pages/{page_id}",
                         data={"archived": True}, method="PATCH")
        print(json.dumps({"status": "deleted", "page_id": page_id}))
    except Exception as e:
        print(json.dumps({"error": str(e), "page_id": page_id}))

# ── Update single field ───────────────────────────────────────────────────────
def update_field(page_id, field_name, field_type, value):
    """Update a single field on a Notion page.
    field_type: number, text, select, date, checkbox
    """
    if field_type == 'number':
        props = {field_name: {"number": float(value)}}
    elif field_type == 'select':
        props = {field_name: {"select": {"name": value}}}
    elif field_type == 'date':
        props = {field_name: {"date": {"start": value}}}
    elif field_type == 'checkbox':
        props = {field_name: {"checkbox": value.lower() in ('true', 'yes', '1', 'done')}}
    else:
        props = {field_name: {"rich_text": [{"text": {"content": str(value)}}]}}
    try:
        result = _request(f"https://api.notion.com/v1/pages/{page_id}",
                         data={"properties": props}, method="PATCH")
        print(json.dumps({"status": "updated", "page_id": page_id,
                          "field": field_name, "new_value": value}))
    except Exception as e:
        print(json.dumps({"error": str(e), "page_id": page_id}))

# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'

    if action == 'search':
        search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)

    elif action == 'read':
        read_page(sys.argv[2])

    elif action == 'create':
        is_db = '--database' in sys.argv
        create_page(sys.argv[2], sys.argv[3],
                    sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '--database' else '', is_db)

    elif action == 'create_db':
        create_database(sys.argv[2], sys.argv[3])

    elif action in ('add_task', 'add-task'):
        if action == 'add-task':
            # Shorthand (CLAUDE.md format): add-task <name> <priority> <due_date> [description]
            # jarvis notion add-task "Title" "High" "2026-03-02"
            add_task(TASKS_TRACKER_DB,
                     sys.argv[2],
                     "Not started",
                     sys.argv[4] if len(sys.argv) > 4 else None,
                     sys.argv[3] if len(sys.argv) > 3 else "Medium",
                     sys.argv[5] if len(sys.argv) > 5 else "")
        else:
            # Full form: add_task <db_id> <name> <status> <due_date> <priority> [description]
            add_task(sys.argv[2], sys.argv[3],
                     sys.argv[4] if len(sys.argv) > 4 else "Not started",
                     sys.argv[5] if len(sys.argv) > 5 else None,
                     sys.argv[6] if len(sys.argv) > 6 else "Medium",
                     sys.argv[7] if len(sys.argv) > 7 else "")

    elif action == 'update_task':
        update_task(sys.argv[2],
                    sys.argv[3] if len(sys.argv) > 3 else None,
                    sys.argv[4] if len(sys.argv) > 4 else None,
                    sys.argv[5] if len(sys.argv) > 5 else None)

    elif action == 'add_expense':
        add_expense(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                    sys.argv[6] if len(sys.argv) > 6 else "Card")

    elif action == 'add_routine':
        add_routine(sys.argv[2], *sys.argv[3:])

    elif action == 'append':
        append_to_page(sys.argv[2], sys.argv[3])

    elif action == 'add_contact':
        add_contact(sys.argv[2], sys.argv[3],
                    sys.argv[4] if len(sys.argv) > 4 else "",
                    sys.argv[5] if len(sys.argv) > 5 else "",
                    sys.argv[6] if len(sys.argv) > 6 else "Other",
                    sys.argv[7] if len(sys.argv) > 7 else "",
                    sys.argv[8] if len(sys.argv) > 8 else "")

    elif action == 'lookup_contact':
        lookup_contact(sys.argv[2], sys.argv[3])

    elif action == 'query':
        query_database(sys.argv[2])

    elif action == 'delete':
        delete_entry(sys.argv[2])

    elif action == 'update_field':
        update_field(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    elif action == 'log_health':
        log_health(sys.argv[2], *sys.argv[3:])

    elif action == 'generate_monthly_report':
        generate_monthly_report(sys.argv[2] if len(sys.argv) > 2 else None)

    elif action == 'log_job':
        log_job_application(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4] if len(sys.argv) > 4 else "Direct",
            sys.argv[5] if len(sys.argv) > 5 else "",
            sys.argv[6] if len(sys.argv) > 6 else "")

    elif action == 'query_jobs':
        query_jobs(sys.argv[2] if len(sys.argv) > 2 else None)

    else:
        print("Usage: notion_tool.py search|read|create|create_db|add_task|add-task|"
              "update_task|add_expense|add_routine|add_contact|lookup_contact|"
              "append|query|delete|update_field|log_health|generate_monthly_report|"
              "log_job|query_jobs ...")
