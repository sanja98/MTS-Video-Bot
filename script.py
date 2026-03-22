import os, json, subprocess, textwrap, requests, re, time, shutil, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 Config & Env
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

# ⚙️ Load External Config
def load_config():
    if not os.path.exists('config.json'):
        return {"subject": "GK", "total_questions": 20, "timer_seconds": 3, "prompt_template": "Create {count} MCQs for {topic}"}
    with open('config.json', 'r') as f:
        return json.load(f)

def get_next_topic():
    if not os.path.exists('topics.txt'): return None
    with open('topics.txt', 'r') as f:
        all_topics = [t.strip() for t in f.read().splitlines() if t.strip()]
    done = []
    if os.path.exists('processed.txt'):
        with open('processed.txt', 'r') as f:
            done = [d.strip() for d in f.read().splitlines() if d.strip()]
    for t in all_topics:
        if t not in done: return t
    return None

def generate_audio(text, filename, is_exp=False):
    temp = f"raw_{int(time.time()*1000)}.mp3"
    rate = "-15%" if is_exp else "-2%"
    res = subprocess.run(['edge-tts', '--voice', 'en-IN-NeerjaNeural', '--text', text, f'--rate={rate}', '--write-media', temp], capture_output=True)
    if res.returncode == 0 and os.path.exists(temp):
        AudioSegment.from_file(temp).set_frame_rate(44100).normalize().export(filename, format="mp3")
        os.remove(temp)
        return True
    return False

def draw_frame(q, opts, timer=None, ans=None, exp=None, head="", subject="GK"):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(f_p): f_p = "arial.ttf"
    try:
        f_m = ImageFont.truetype(f_p, 55); f_s = ImageFont.truetype(f_p, 45); f_t = ImageFont.truetype(f_p, 130)
    except:
        f_m = f_s = f_t = ImageFont.load_default()

    # Colors
    header_clr = (255, 193, 7) if subject == "GK" else (100, 255, 218)
    
    # 🛠️ FIXED: Full Width Header Box
    draw.rectangle([0, 0, W, 120], fill=header_clr)
    
    # 🛠️ FIXED: Text starts from Left (100px) instead of Center, so it won't cut
    draw.text((100, 35), head, fill=(15, 23, 42), font=f_m)
    
    # Question
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    
    y = 380
    for k in ['A', 'B', 'C', 'D']:
        v = opts.get(k, "N/A")
        clr = (46, 204, 113) if (ans and k==ans) else (51, 65, 85)
        draw.rectangle([100, y, 1750, y+85], fill=clr, outline=header_clr, width=3)
        draw.text((125, y+18), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 110
        
    if timer: draw.text((1800, 450), str(timer), fill=(255, 80, 80), font=f_t)
    if exp: draw.text((100, 850), "\n".join(textwrap.wrap(f"💡 {exp}", 80)), fill=(255, 255, 100), font=f_s)
    
    img.save("frame.jpg")
    return "frame.jpg"

def main():
    cfg = load_config()
    topic = get_next_topic()
    if not topic: print("🎉 Finished!"); return
    
    prompt = cfg['prompt_template'].format(count=cfg['total_questions'], subject=cfg['subject'], topic=topic)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60).json()
        raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)

        audio_dir = "temp_audio"
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        os.makedirs(audio_dir)

        sr = 44100; t_sfx = np.linspace(0, 0.1, int(sr*0.1), False)
        write("tick.wav", sr, (np.sin(800*2*np.pi*t_sfx)*32767).astype(np.int16))
        tick = mp.AudioFileClip("tick.wav")

        clips = []
        for j, item in enumerate(data, 1):
            q, opt = item.get('question'), item.get('options')
            if not q or not opt: continue
            ans, exp = item.get('answer', 'A'), item.get('explanation', 'Important Topic.')
            h = f"{cfg['subject'].upper()}: {topic.upper()}"
            
            qa = f"{audio_dir}/q{j}.mp3"
            if generate_audio(f"Question {j}. {q}", qa):
                q_aud = mp.AudioFileClip(qa)
                clips.append(mp.ImageClip(draw_frame(q, opt, head=h, subject=cfg['subject'])).set_duration(q_aud.duration).set_audio(q_aud))
                for t in range(cfg['timer_seconds'], 0, -1):
                    clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=h, subject=cfg['subject'])).set_duration(1).set_audio(tick))
                aa = f"{audio_dir}/a{j}.mp3"
                if generate_audio(f"Answer {ans}. {exp}", aa, is_exp=True):
                    a_aud = mp.AudioFileClip(aa)
                    clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=h, subject=cfg['subject'])).set_duration(a_aud.duration + 1).set_audio(a_aud))

        if clips:
            out_name = "video.mp4"
            mp.concatenate_videoclips(clips, method="compose").write_videofile(out_name, fps=24, codec="libx264", preset="ultrafast", logger=None)
            with open(out_name, 'rb') as v:
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={'chat_id': USER_ID, 'caption': f"📚 {cfg['subject']}: {topic}"}, files={'video': v})
            with open('processed.txt', 'a') as f: f.write(topic + "\n")
            print("🏁 Success!")
    except Exception as e: print(f"❌ Error: {e}")
    finally:
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        if os.path.exists("tick.wav"): os.remove("tick.wav")

if __name__ == "__main__":
    main()
