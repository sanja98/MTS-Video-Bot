import os, json, subprocess, textwrap, requests, re, time, shutil, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 1. Strict Env Validation (Fixes Bug #1 & #2)
def validate_setup():
    k1 = os.environ.get('KEY1')
    k2 = os.environ.get('KEY2')
    token = os.environ.get('TG_TOKEN')
    uid = os.environ.get('USER_ID')
    if not all([k1, token, uid]):
        raise ValueError("❌ Missing CRITICAL Secrets (KEY1, TG_TOKEN, or USER_ID)")
    return [k1, k2 if k2 else k1], token, uid

try:
    KEYS, TG_TOKEN, USER_ID = validate_setup()
except Exception as e:
    print(e); exit(1)

# 📂 2. Secure File Operations (Fixes Bug #6)
def get_next_topic():
    if not os.path.exists('topics.txt'): return None
    try:
        with open('topics.txt', 'r') as f:
            all_topics = [t.strip() for t in f.read().splitlines() if t.strip()]
        done = []
        if os.path.exists('processed.txt'):
            with open('processed.txt', 'r') as f:
                done = [d.strip() for d in f.read().splitlines() if d.strip()]
        for t in all_topics:
            if t not in done: return t
    except IOError as e:
        print(f"❌ File Read Error: {e}")
    return None

def clean_txt(text):
    return re.sub(r'[*_#\[\]()\\/]', '', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

# 🎤 3. Subprocess with Error Logging (Fixes Bug #5)
def generate_audio(text, filename, is_exp=False):
    temp = f"raw_{int(time.time()*1000)}.mp3"
    rate = "-15%" if is_exp else "-2%"
    res = subprocess.run(['edge-tts', '--voice', 'en-IN-NeerjaNeural', '--text', clean_txt(text), 
                         f'--rate={rate}', '--write-media', temp], capture_output=True)
    if res.returncode != 0:
        print(f"❌ edge-tts Error: {res.stderr.decode()}")
        return False
    if os.path.exists(temp):
        AudioSegment.from_file(temp).set_frame_rate(44100).normalize().export(filename, format="mp3")
        os.remove(temp)
        return True
    return False

# 🖼️ 4. Dynamic Font Path (Fixes Bug #4 & #8)
def get_font():
    paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in paths:
        if os.path.exists(p): return p
    return None

def draw_frame(q, opts, timer=None, ans=None, exp=None, head=""):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = get_font()
    try:
        f_m = ImageFont.truetype(f_p, 55) if f_p else ImageFont.load_default()
        f_s = ImageFont.truetype(f_p, 45) if f_p else ImageFont.load_default()
        f_t = ImageFont.truetype(f_p, 130) if f_p else ImageFont.load_default()
    except (OSError, IOError):
        f_m = f_s = f_t = ImageFont.load_default()

    draw.rectangle([0, 0, W, 120], fill=(255, 193, 7))
    draw.text((W//2-300, 35), head, fill=(15, 23, 42), font=f_m)
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    y = 380
    for k in ['A', 'B', 'C', 'D']:
        v = opts.get(k, "N/A")
        clr = (46, 204, 113) if (ans and k==ans) else (51, 65, 85)
        draw.rectangle([100, y, 1550, y+85], fill=clr, outline=(255, 193, 7), width=3)
        draw.text((125, y+18), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 110
    if timer: draw.text((1650, 450), str(timer), fill=(255, 80, 80), font=f_t)
    if exp: draw.text((100, 850), "\n".join(textwrap.wrap(f"💡 {clean_txt(exp)}", 75)), fill=(255, 255, 100), font=f_s)
    img.save("frame.jpg")
    return "frame.jpg"

def main():
    topic = get_next_topic()
    if not topic: print("🎉 Finished!"); return
    print(f"🚀 Topic: {topic}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"Strict JSON array of 25 SSC MTS GK MCQs for '{topic}' in English. Keys: 'question', 'options' (A,B,C,D), 'answer', 'explanation'. No markdown."
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60).json()
        # 🛡️ Fix Bug #2 & #6 (JSON Validation)
        if 'candidates' not in res: raise ValueError(f"API Error: {res}")
        raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        if not isinstance(data, list): raise ValueError("Invalid JSON Format")

        audio_dir = "temp_audio"
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        os.makedirs(audio_dir)

        # SFX
        sr = 44100; t_sfx = np.linspace(0, 0.1, int(sr*0.1), False)
        write("tick.wav", sr, (np.sin(800*2*np.pi*t_sfx)*32767).astype(np.int16))
        tick = mp.AudioFileClip("tick.wav")

        clips = []
        for j, item in enumerate(data, 1):
            # 🛡️ Fix Bug #7 (Validation)
            q = item.get('question'); opt = item.get('options')
            if not q or not opt: continue
            ans = item.get('answer', 'A'); exp = item.get('explanation', 'Important for SSC MTS.')
            
            qa = f"{audio_dir}/q{j}.mp3"
            if generate_audio(f"Question {j}. {q}", qa):
                q_aud = mp.AudioFileClip(qa)
                clips.append(mp.ImageClip(draw_frame(q, opt, head=f"GK: {topic.upper()}")).set_duration(q_aud.duration).set_audio(q_aud))
                for t in range(3, 0, -1): clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=f"GK: {topic.upper()}")).set_duration(1).set_audio(tick))
                aa = f"{audio_dir}/a{j}.mp3"
                if generate_audio(f"Answer is {ans}. {exp}", aa, is_exp=True):
                    a_aud = mp.AudioFileClip(aa)
                    clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=f"GK: {topic.upper()}")).set_duration(a_aud.duration + 1).set_audio(a_aud))

        # 🛡️ Fix Bug #3 (Empty Clips)
        if not clips: print("❌ No clips generated!"); return

        out_name = "gk_video.mp4"
        final_vid = mp.concatenate_videoclips(clips, method="compose")
        final_vid.write_videofile(out_name, fps=24, codec="libx264", preset="ultrafast", logger=None)
        
        if os.path.exists(out_name) and os.path.getsize(out_name) > 0:
            with open(out_name, 'rb') as v:
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={'chat_id': USER_ID, 'caption': f"✅ GK: {topic}"}, files={'video': v})
            with open('processed.txt', 'a') as f: f.write(topic + "\n")
            print("🏁 Success!")

    except Exception as e: print(f"❌ Error: {e}")
    finally:
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        if os.path.exists("tick.wav"): os.remove("tick.wav")

if __name__ == "__main__":
    main()
