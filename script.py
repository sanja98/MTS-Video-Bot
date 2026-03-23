import os, json, requests, random, textwrap, subprocess, time, shutil, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 🔐 Credentials
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')
YT_TOKEN_JSON = os.environ.get('YT_TOKEN_JSON')

def load_hybrid_config():
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                c = json.load(f)
                if c.get("subject") and c.get("prompt_template"):
                    return c
        except: pass
    return {
        "subject": "World GK",
        "total_questions": 10,
        "timer_seconds": 5,
        "prompt_template": "Create {count} high-quality MCQs for {topic} in English. Return ONLY a JSON list of objects with keys: question, options (dict A,B,C,D), answer (letter), explanation, v_title (viral title), v_desc (viral description)."
    }

def upload_to_youtube(file_path, title, description, thumbnail_path=None):
    try:
        if not YT_TOKEN_JSON: return
        creds = Credentials.from_authorized_user_info(json.loads(YT_TOKEN_JSON))
        youtube = build('youtube', 'v3', credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "tags": ["GK", "GlobalQuiz", "Facts"], "categoryId": "27"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            },
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
        )
        response = request.execute()
        if thumbnail_path:
            youtube.thumbnails().set(videoId=response['id'], media_body=MediaFileUpload(thumbnail_path)).execute()
        print("🚀 YouTube Upload Success!")
    except Exception as e: print(f"❌ YT Error: {e}")

def create_thumbnail(topic):
    W, H = (1280, 720)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(f_p): f_p = "arial.ttf"
    f_l = ImageFont.truetype(f_p, 80); f_s = ImageFont.truetype(f_p, 50)
    draw.rectangle([0, 0, W, 120], fill=(255, 193, 7))
    draw.text((50, 20), "WORLD GK CHALLENGE", fill=(0,0,0), font=f_l)
    draw.text((50, 300), topic.upper()[:25], fill=(255, 255, 255), font=f_l)
    draw.text((50, 450), "Can you score 10/10?", fill=(0, 255, 200), font=f_s)
    img.save("thumb.jpg"); return "thumb.jpg"

def draw_frame(q, opts, timer=None, ans=None, exp=None, head="", subject="GK"):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(f_p): f_p = "arial.ttf"
    f_m = ImageFont.truetype(f_p, 50); f_s = ImageFont.truetype(f_p, 40); f_t = ImageFont.truetype(f_p, 150)

    draw.rectangle([0, 0, W, 100], fill=(255, 193, 7))
    draw.text((60, 20), head[:70], fill=(15, 23, 42), font=f_m)
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    
    y = 380
    for k in ['A', 'B', 'C', 'D']:
        v = opts.get(k, "N/A")
        box_clr = (46, 204, 113) if (ans and k==ans) else (30, 41, 59)
        draw.rectangle([100, y, 1550, y+80], fill=box_clr, outline=(71, 85, 105), width=2)
        draw.text((130, y+15), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 105
        
    if timer: 
        draw.ellipse([1620, 400, 1850, 630], outline=(255, 193, 7), width=8)
        draw.text((1690, 440), str(timer), fill=(255, 193, 7), font=f_t)

    if exp: 
        exp_text = "\n".join(textwrap.wrap(f"💡 Info: {exp}", 85))
        draw.rectangle([100, 820, 1820, 1040], fill=(20, 30, 50), outline=(255, 193, 7), width=3)
        draw.text((130, 840), exp_text, fill=(200, 255, 200), font=f_s)

    img.save("frame.jpg"); return "frame.jpg"

def generate_audio(text, filename, is_exp=False):
    temp = f"raw_{int(time.time()*1000)}.mp3"
    rate = "-12%" if is_exp else "-2%"
    subprocess.run(['edge-tts', '--voice', 'en-IN-NeerjaNeural', '--text', text, f'--rate={rate}', '--write-media', temp])
    if os.path.exists(temp):
        AudioSegment.from_file(temp).export(filename, format="mp3")
        os.remove(temp)
        return True
    return False

def get_next_topic():
    global_topics = ["Space Mysteries", "Ancient History", "Geography", "Ocean Life", "Mega Structures", "Inventions"]
    if os.path.exists('topics.txt'):
        with open('topics.txt', 'r') as f:
            ts = [t.strip() for t in f.read().splitlines() if t.strip()]
        if ts:
            done = open('processed.txt', 'r').read().splitlines() if os.path.exists('processed.txt') else []
            for t in ts:
                if t not in done: return t
    return random.choice(global_topics)

def main():
    audio_dir = "temp_audio"
    cfg = load_hybrid_config()
    topic = get_next_topic()
    prompt = cfg['prompt_template'].format(count=cfg.get('total_questions', 10), topic=topic)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        raw = re.sub(r'```json\s*|\s*```', '', res['candidates'][0]['content']['parts'][0]['text']).strip()
        data = json.loads(raw)

        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        os.makedirs(audio_dir)

        sr = 44100; t_s = np.linspace(0, 0.1, int(sr*0.1), False)
        write("tick.wav", sr, (np.sin(1000*2*np.pi*t_s)*32767).astype(np.int16))
        tick = mp.AudioFileClip("tick.wav")

        clips = []
        for j, item in enumerate(data, 1):
            q, opt, ans, exp = item['question'], item['options'], item['answer'], item['explanation']
            h = f"{cfg.get('subject', 'GK')}: {topic.upper()}"
            qa = f"{audio_dir}/q{j}.mp3"
            if generate_audio(f"Question {j}: {q}", qa):
                q_aud = mp.AudioFileClip(qa)
                clips.append(mp.ImageClip(draw_frame(q, opt, head=h, subject=cfg['subject'])).set_duration(q_aud.duration).set_audio(q_aud))
                for t in range(cfg.get('timer_seconds', 5), 0, -1):
                    clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=h, subject=cfg['subject'])).set_duration(1).set_audio(tick))
                aa = f"{audio_dir}/a{j}.mp3"
                if generate_audio(f"The answer is {ans}. {exp}", aa, is_exp=True):
                    a_aud = mp.AudioFileClip(aa)
                    clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=h, subject=cfg['subject'])).set_duration(a_aud.duration + 1).set_audio(a_aud))

        if clips:
            final_v = "video.mp4"
            mp.concatenate_videoclips(clips, method="compose").write_videofile(final_v, fps=24, codec="libx264", logger=None)
            
            v_title = data[0].get('v_title', f"Ultimate {topic} Quiz")
            v_desc = data[0].get('v_desc', f"Test your knowledge on {topic}!")
            thumb = create_thumbnail(topic)
            
            upload_to_youtube(final_v, v_title, v_desc, thumbnail_path=thumb)
            with open(final_v, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={'chat_id': USER_ID, 'caption': v_title}, files={'video': f})
            
            if os.path.exists('topics.txt'):
                with open('processed.txt', 'a') as f: f.write(topic + "\n")
                
    except Exception as e: print(f"❌ Error: {e}")
    finally:
        if os.path.exists(audio_dir): shutil.rmtree(audio_dir)
        if os.path.exists("tick.wav"): os.remove("tick.wav")

if __name__ == "__main__":
    main()
