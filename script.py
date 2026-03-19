import os, json, subprocess, textwrap, requests, re, time, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 Config
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

def get_next_topic():
    # Saare topics ki list
    with open('topics.txt', 'r') as f:
        all_topics = f.read().splitlines()
    
    # Jo ho chuke hain unki list
    if not os.path.exists('processed.txt'):
        open('processed.txt', 'w').close()
        
    with open('processed.txt', 'r') as f:
        done = f.read().splitlines()
    
    for t in all_topics:
        if t not in done: return t
    return None

# ... (generate_audio aur draw_frame functions wahi rahenge) ...

def main():
    topic = get_next_topic()
    if not topic:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': USER_ID, 'text': "🏆 Reasoning Syllabus Complete!"})
        return

    print(f"🎬 Processing: {topic}")
    
    # 📡 Fetch from AI
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"JSON array of 20 SSC MTS {topic} MCQs. Plain Hinglish. No symbols/markdown."
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        
        # --- Rendering Logic Yahan ---
        # (Wahi 20 Qs wala loop jo humne pehle use kiya)
        
        # Video banne ke baad mark as done
        with open('processed.txt', 'a') as f:
            f.write(topic + "\n")
            
        print(f"✅ {topic} Finished!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
    
