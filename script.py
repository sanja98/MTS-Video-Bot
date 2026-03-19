import os, json, subprocess, textwrap, requests, re, time, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# Config
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

def get_next_topic():
    with open('topics.txt', 'r') as f:
        all_topics = f.read().splitlines()
    if os.path.exists('processed.txt'):
        with open('processed.txt', 'r') as f:
            done = f.read().splitlines()
    else:
        done = []
    
    for t in all_topics:
        if t not in done: return t
    return None

# ... (Purane generate_audio aur draw_frame functions yahan rehne dena) ...

def main():
    topic = get_next_topic()
    if not topic:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': USER_ID, 'text': "🏆 Full Syllabus Complete!"})
        return

    print(f"🎬 Processing: {topic}")
    
    # 📡 Fetch Data (Yahan hum loop ke hisab se Key rotate kar sakte hain)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"JSON array of 20 SSC MTS {topic} MCQs. Plain Hinglish. No markdown."
    
    res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
    raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
    data = json.loads(raw)

    # --- Video Rendering Logic (Wahi same jo pehle chal gaya) ---
    # ... (Video clips aur rendering ka code yahan paste karein) ...

    # Mark as Done
    with open('processed.txt', 'a') as f:
        f.write(topic + "\n")
    
    # Send to TG
    # ... (Telegram send logic) ...

if __name__ == "__main__":
    main()
    
