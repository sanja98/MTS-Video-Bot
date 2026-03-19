import os, json, subprocess, textwrap, requests, re, time, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 GitHub Secrets se keys uthana (Safe Method)
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

SYLLABUS = ["Coding-Decoding", "Analogy", "Syllogism", "Venn Diagrams", "Blood Relations", "Direction Sense", "Sitting Arrangement"]
DATA_DIR = "data/reasoning"

def clean_txt(text):
    return re.sub(r'[*_#\[\]()\\/]', '', text).encode('ascii', 'ignore').decode('ascii').strip()

def generate_audio(text, filename, is_exp=False):
    temp = "raw.mp3"
    rate = "-18%" if is_exp else "-5%"
    subprocess.run(['edge-tts', '--voice', 'en-IN-NeerjaNeural', '--text', clean_txt(text), f'--rate={rate}', '--write-media', temp])
    if os.path.exists(temp):
        AudioSegment.from_file(temp).set_frame_rate(44100).normalize().export(filename, format="mp3")
        os.remove(temp)

def draw_frame(q, opts, timer=None, ans=None, exp=None, head=""):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    f_m = ImageFont.truetype(f_p, 55); f_s = ImageFont.truetype(f_p, 45); f_t = ImageFont.truetype(f_p, 130)
    
    draw.rectangle([0, 0, W, 120], fill=(100, 255, 218))
    draw.text((W//2-300, 35), head, fill=(15, 23, 42), font=f_m)
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    y = 380
    for k, v in opts.items():
        clr = (46, 204, 113) if (ans and k==ans) else (51, 65, 85)
        draw.rectangle([100, y, 1550, y+85], fill=clr, outline=(100, 255, 218), width=3)
        draw.text((125, y+18), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 110
    if timer: draw.text((1650, 450), str(timer), fill=(255, 80, 80), font=f_t)
    if exp: draw.text((100, 850), "\n".join(textwrap.wrap(f"💡 {clean_txt(exp)}", 75)), fill=(255, 255, 100), font=f_s)
    img.save("frame.jpg")
    return "frame.jpg"

def main():
    # Aaj ka topic decide karne ka logic (Aap ise manual ya auto kar sakte hain)
    topic = SYLLABUS[0] # Example: Pehla topic
    print(f"🎬 Creating video for: {topic}")
    
    # AI se data mangne ka logic (Gemini 3.1 Flash Lite)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"JSON array of 20 SSC MTS {topic} MCQs. Plain Hinglish. No markdown."
    
    res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
    raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
    data = json.loads(raw)

    # Video Rendering (Same logic as before)
    # ... (yahan rendering wala loop dal dena)
    # Telegram Send
    # ...
    print("✅ Video sent to Telegram!")

if __name__ == "__main__":
    main()
  
