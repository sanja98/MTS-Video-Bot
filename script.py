import os, json, subprocess, textwrap, requests, re, time, shutil, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 1. ENV Validation (Copilot's Fix)
def get_env(name):
    val = os.environ.get(name)
    if not val:
        print(f"❌ Missing Secret: {name}")
        return None
    return val

KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = get_env('TG_TOKEN')
USER_ID = get_env('USER_ID')

# 📂 2. Get Next Topic with Error Handling
def get_next_topic():
    try:
        if not os.path.exists('topics.txt'): return None
        with open('topics.txt', 'r') as f:
            all_topics = [t.strip() for t in f.read().splitlines() if t.strip()]
        
        done = []
        if os.path.exists('processed.txt'):
            with open('processed.txt', 'r') as f:
                done = [d.strip() for d in f.read().splitlines() if d.strip()]
        
        for t in all_topics:
            if t not in done: return t
    except Exception as e:
        print(f"⚠️ File error: {e}")
    return None

def clean_txt(text):
    return re.sub(r'[*_#\[\]()\\/]', '', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

# 🎤 3. Smart Audio Generation
def generate_audio(text, filename, is_exp=False):
    temp = f"raw_{int(time.time()*1000)}.mp3"
    rate = "-15%" if is_exp else "-2%"
    res = subprocess.run(['edge-tts', '--voice', 'en-IN-NeerjaNeural', '--text', clean_txt(text), f'--rate={rate}', '--write-media', temp], capture_output=True)
    
    if res.returncode == 0 and os.path.exists(temp):
        AudioSegment.from_file(temp).set_frame_rate(44100).normalize().export(filename, format="mp3")
        os.remove(temp)
        return True
    return False

# 🖼️ 4. Frame Drawing (Smart Font)
def draw_frame(q, opts, timer=None, ans=None, exp=None, head=""):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Font Fallback (Copilot's Fix)
    f_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(f_path): f_path = "arial.ttf" # Fallback for local testing
    
    try:
        f_m = ImageFont.truetype(f_path, 55); f_s = ImageFont.truetype(f_path, 45); f_t = ImageFont.truetype(f_path, 130)
    except:
        f_m = f_s = f_t = ImageFont.load_default()

    draw.rectangle([0, 0, W, 120], fill=(255, 193, 7)) # GK Yellow
    draw.text((W//2-300, 35), head, fill=(15, 23, 42), font=f_m)
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    
    y = 380
    for k, v in opts.items():
        clr = (46, 204, 113) if (ans and k==ans) else (51, 65, 85)
        draw.rectangle([100, y, 1550, y+85], fill=clr, outline=(255, 193, 7), width=3)
        draw.text((125, y+18), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 110
        
    if timer: draw.text((1650, 450), str(timer), fill=(255, 80, 80), font=f_t)
    if exp: draw.text((100, 850), "\n".join(textwrap.wrap(f"💡 {clean_txt(exp)}", 75)), fill=(255, 255, 100), font=f_s)
    img.save("frame.jpg")
    return "frame.jpg"

def main():
    if not TG_TOKEN or not USER_ID: return
    
    topic = get_next_topic()
    if not topic:
        print("🎉 Mission Accomplished!")
        return

    print(f"🚀 Processing GK: {topic}")
    
    # English Only Prompt (Your Request)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"JSON array of 25 SSC MTS GK MCQs for '{topic}'. Question/Options MUST be in English. Short English explanation. Keys: 'question', 'options' (A,B,C,D), 'answer', 'explanation'. No markdown."
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30).json()
        raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        
        audio_dir = "temp_audio"
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        os.makedirs(audio_dir)

        # SFX Generation
        sr = 44100; t_sfx = np.linspace(0, 0.1, int(sr*0.1), False)
        write("tick.wav", sr, (np.sin(800*2*np.pi*t_sfx)*32767).astype(np.int16))
        tick = mp.AudioFileClip("tick.wav")

        clips = []
        for j, item in enumerate(data, 1):
            q, opt = item.get('question', 'N/A'), item.get('options', {})
            ans, exp = item.get('answer', 'A'), item.get('explanation', 'Important Topic.')
            
            h = f"GK: {topic.upper()}"
            qa = f"{audio_dir}/q{j}.mp3"
            if generate_audio(f"Question {j}. {q}", qa):
                q_aud = mp.AudioFileClip(qa)
                clips.append(mp.ImageClip(draw_frame(q, opt, head=h)).set_duration(q_aud.duration).set_audio(q_aud))
                # 3 Second Timer
                for t in range(3, 0, -1):
                    clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=h)).set_duration(1).set_audio(tick))
                
                aa = f"{audio_dir}/a{j}.mp3"
                if generate_audio(f"Answer is {ans}. {exp}", aa, is_exp=True):
                    a_aud = mp.AudioFileClip(aa)
                    clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=h)).set_duration(a_aud.duration + 1).set_audio(a_aud))

        if clips:
            out_name = "gk_video.mp4"
            final_vid = mp.concatenate_videoclips(clips, method="compose")
            final_vid.write_videofile(out_name, fps=24, codec="libx264", preset="ultrafast", logger=None)
            
            if os.path.exists(out_name):
                with open(out_name, 'rb') as v:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                                  data={'chat_id': USER_ID, 'caption': f"✅ GK Topic: {topic}"}, files={'video': v})
                with open('processed.txt', 'a') as f: f.write(topic + "\n")
                print("🏁 Success!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        if os.path.exists("tick.wav"): os.remove("tick.wav")

if __name__ == "__main__":
    main()
