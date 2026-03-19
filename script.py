import os, json, subprocess, textwrap, requests, re, time, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 Config from Secrets
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

def get_next_topic():
    if not os.path.exists('topics.txt'):
        print("⚠️ topics.txt file nahi mili!")
        return "Coding-Decoding" # Default
        
    with open('topics.txt', 'r') as f:
        all_topics = f.read().splitlines()
    
    done = []
    if os.path.exists('processed.txt'):
        with open('processed.txt', 'r') as f:
            done = f.read().splitlines()
    
    for t in all_topics:
        if t.strip() and t.strip() not in done:
            return t.strip()
    return None

def clean_txt(text):
    return re.sub(r'[*_#\[\]()\\/]', '', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

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
    topic = get_next_topic()
    if not topic:
        print("🎉 All topics finished! Syllabus Complete.")
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': USER_ID, 'text': "🏆 Reasoning Syllabus Over!"})
        except: pass
        return

    print(f"🚀 Processing Topic: {topic}")
    
    # AI se strictly mangenge taaki galti na kare
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"Create a strictly formatted JSON array of 10 SSC MTS Reasoning MCQs for '{topic}'. Keys must be exactly: 'question', 'options' (with A, B, C, D), 'answer', and 'explanation'. Plain Hinglish. No markdown."
    
    try:
        print("📡 Fetching data from Gemini...")
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        print(f"✅ Data fetched successfully! Total questions: {len(data)}")

        audio_dir = "temp_audio"; os.makedirs(audio_dir, exist_ok=True)
        sr = 44100; t_sfx = np.linspace(0, 0.1, int(sr*0.1), False)
        write("tick.wav", sr, (np.sin(800*2*np.pi*t_sfx)*32767).astype(np.int16))
        tick = mp.AudioFileClip("tick.wav")

        clips = []
        for j, item in enumerate(data, 1):
            # 🛡️ THE SAFETY NET: Agar AI koi key miss kare, toh script default value use karegi
            q = item.get('question', f'Find the correct logic for this question.')
            opt = item.get('options', {'A': 'Option 1', 'B': 'Option 2', 'C': 'Option 3', 'D': 'Option 4'})
            ans = item.get('answer', 'A')
            exp = item.get('explanation', item.get('exp', 'Apply correct logical steps to solve this.'))
            
            h = f"REASONING: {topic.upper()}"
            qa = f"{audio_dir}/q{j}.mp3"; generate_audio(f"Question {j}. {q}", qa)
            q_aud = mp.AudioFileClip(qa); clips.append(mp.ImageClip(draw_frame(q, opt, head=h)).set_duration(q_aud.duration).set_audio(q_aud))
            
            for t in range(5, 0, -1): clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=h)).set_duration(1).set_audio(tick))
            
            aa = f"{audio_dir}/a{j}.mp3"; generate_audio(f"Correct answer is {ans}. {exp}", aa, is_exp=True)
            a_aud = mp.AudioFileClip(aa); clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=h)).set_duration(a_aud.duration + 1).set_audio(a_aud))

        out_name = "final_video.mp4"
        print("🎥 Rendering Video...")
        mp.concatenate_videoclips(clips, method="compose").write_videofile(out_name, fps=24, codec="libx264", preset="ultrafast", logger=None)

        # 📲 Telegram Send
        print("📲 Sending to Telegram...")
        with open(out_name, 'rb') as v:
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={'chat_id': USER_ID, 'caption': f"📚 Topic: {topic} | Auto-Generated"}, files={'video': v})
            print(f"✅ TG Send Response: {r.status_code}")

        # ✅ Mark as Done in file
        with open('processed.txt', 'a') as f:
            f.write(topic + "\n")
        print("💾 Progress saved!")
            
    except Exception as e:
        print(f"❌ Python Error occurred: {e}")

if __name__ == "__main__":
    main()
