#!/usr/bin/env python3
"""Transcribe audio using OpenAI Whisper API."""
import sys, json, os, glob

env_path = os.path.expanduser('~/.openclaw/.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('OPENAI_API_KEY='):
                os.environ['OPENAI_API_KEY'] = line.strip().split('=', 1)[1]

MEDIA_DIR = '/home/YOUR_USERNAME/.openclaw/media/inbound'

def find_latest():
    files = glob.glob(os.path.join(MEDIA_DIR, '*.ogg'))
    files += glob.glob(os.path.join(MEDIA_DIR, '*.mp3'))
    files += glob.glob(os.path.join(MEDIA_DIR, '*.m4a'))
    files += glob.glob(os.path.join(MEDIA_DIR, '*.wav'))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def transcribe(filepath):
    from openai import OpenAI
    client = OpenAI()
    with open(filepath, 'rb') as f:
        result = client.audio.transcriptions.create(model='whisper-1', file=f)
    print(json.dumps({"text": result.text, "file": filepath}))

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'latest'
    if arg == 'latest':
        fp = find_latest()
        if not fp:
            print(json.dumps({"error": "No audio files found"}))
            sys.exit(1)
    else:
        fp = arg
    transcribe(fp)
