#!/usr/bin/env python3
"""Memory tool — saves facts with verification."""
import sys, json, os

MEMORY_PATH = '/home/YOUR_USERNAME/.openclaw/workspace/MEMORY.md'

def save(fact):
    fact = fact.replace("USD", "$")  # Shell eats $, LLM writes USD, we fix it
    before = os.path.getsize(MEMORY_PATH)
    with open(MEMORY_PATH, 'a') as f:
        f.write(f"\n- {fact}")
    after = os.path.getsize(MEMORY_PATH)
    if after > before:
        print(json.dumps({"status": "SAVED_TO_DISK", "fact": fact, "file_size_before": before, "file_size_after": after}))
    else:
        print(json.dumps({"status": "FAILED", "error": "File size unchanged"}))

def read():
    with open(MEMORY_PATH, 'r') as f:
        content = f.read()
    print(content)

def search(query):
    with open(MEMORY_PATH, 'r') as f:
        lines = f.readlines()
    matches = [l.strip() for l in lines if query.lower() in l.lower()]
    if matches:
        print(json.dumps({"matches": matches}))
    else:
        print(json.dumps({"matches": [], "message": "Nothing found"}))


def replace(old_text, new_text):
    """Replace an existing memory line containing old_text with new_text."""
    new_text = new_text.replace("USD", "$")
    with open(MEMORY_PATH, 'r') as f:
        lines = f.readlines()
    
    found = False
    new_lines = []
    for line in lines:
        if old_text.lower() in line.lower() and not found:
            new_lines.append(f"- {new_text}\n")
            found = True
        else:
            new_lines.append(line)
    
    if found:
        with open(MEMORY_PATH, 'w') as f:
            f.writelines(new_lines)
        print(json.dumps({"status": "REPLACED", "old_match": old_text, "new_fact": new_text}))
    else:
        print(json.dumps({"status": "NOT_FOUND", "searched_for": old_text, "hint": "Use save instead to add new fact"}))

def delete_fact(search_text):
    """Delete a memory line containing search_text."""
    with open(MEMORY_PATH, 'r') as f:
        lines = f.readlines()
    
    new_lines = [l for l in lines if search_text.lower() not in l.lower()]
    removed = len(lines) - len(new_lines)
    
    if removed > 0:
        with open(MEMORY_PATH, 'w') as f:
            f.writelines(new_lines)
        print(json.dumps({"status": "DELETED", "matched": search_text, "lines_removed": removed}))
    else:
        print(json.dumps({"status": "NOT_FOUND", "searched_for": search_text}))

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if action == 'save':
        save(' '.join(sys.argv[2:]))
    elif action == 'read':
        read()
    elif action == 'search':
        search(' '.join(sys.argv[2:]))
    elif action == 'replace':
        replace(sys.argv[2], sys.argv[3])
    elif action == 'delete':
        delete_fact(' '.join(sys.argv[2:]))
    else:
        print("Usage: memory_tool.py save|read|search|replace|delete <text>")
