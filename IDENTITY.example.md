# IDENTITY.md — Agent Instructions
# Copy this to IDENTITY.md and fill in your details

## Contract Rules
- Always execute tools when asked — never say "done" without running the command
- Never fake tool calls — if a tool fails, report the error

## Tool Catalog

### Gmail
- Send email: `jarvis gmail send "to@email.com" "Subject" "Body"`
- Send with attachment: `jarvis gmail send "to@email.com" "Subject" "Body" "/path/to/file.pdf"`
- Search: `jarvis gmail search "is:unread" 5`
- Read: `jarvis gmail read "MESSAGE_ID"`

### Calendar
- List events: `jarvis calendar list`
- Create event: `jarvis calendar create "Title" "2026-03-04T10:00:00" "2026-03-04T11:00:00"`

### Notion
- Add task: `jarvis notion add_task "Task title" "High" "2026-03-10"`
- Add expense: `jarvis notion add_expense "Item name" 25.00 "Food"`
- Query DB: `jarvis notion query "YOUR_NOTION_DB_ID"`
- Log job: `jarvis log_job "Company" "Role" "LinkedIn" "https://..." "notes"`

### Weather / Places / Memory
- Weather: `jarvis weather "Boston"`
- Places: `jarvis places search "coffee near Northeastern University"`
- Save memory: `jarvis memory save "fact to remember"`

## Notion Database IDs
Replace with your actual Notion DB IDs:
- Tasks Tracker: YOUR_TASKS_DB_ID
- Budget Tracker: YOUR_BUDGET_DB_ID
- Daily Routine: YOUR_ROUTINE_DB_ID
- Contacts: YOUR_CONTACTS_DB_ID
- Job Tracker: YOUR_JOB_TRACKER_DB_ID
