import os, json, subprocess, textwrap, requests, re, time, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import moviepy.editor as mp
from scipy.io.wavfile import write

# 🔐 Load Secrets
KEYS = [os.environ.get('KEY1'), os.environ.get('KEY2')]
TG_TOKEN = os.environ.get('TG_TOKEN')
USER_ID = os.environ.get('USER_ID')

SYLLABUS = ["Coding-Decoding", "Analogy", "Syllogism", "Venn Diagrams"]

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
    topic = SYLLABUS[0]
    print(f"🎬 Starting: {topic}")
    
    # 📡 Get Data from Gemini
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={KEYS[0]}"
    prompt = f"Create a JSON array of 10 SSC MTS Reasoning MCQs for '{topic}'. Format: [{{'question': '...', 'options': {{'A': '...', 'B': '...', 'C': '...', 'D': '...'}}, 'answer': 'A', 'explanation': '...'}}]. No markdown."
    
    res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
    raw = res['candidates'][0]['content']['parts'][0]['text'].strip().replace("```json", "").replace("```", "")
    data = json.loads(raw)

    audio_dir = "temp_audio"; os.makedirs(audio_dir, exist_ok=True)
    sr = 44100; t_sfx = np.linspace(0, 0.1, int(sr*0.1), False)
    write("tick.wav", sr, (np.sin(800*2*np.pi*t_sfx)*32767).astype(np.int16))
    tick = mp.AudioFileClip("tick.wav")

    clips = []
    for j, item in enumerate(data, 1):
        q, opt, ans, exp = item['question'], item['options'], item['answer'], item['explanation']
        h = f"REASONING: {topic.upper()}"
        
        qa = f"{audio_dir}/q{j}.mp3"; generate_audio(f"Question {j}. {q}", qa)
        q_aud = mp.AudioFileClip(qa); clips.append(mp.ImageClip(draw_frame(q, opt, head=h)).set_duration(q_aud.duration).set_audio(q_aud))
        for t in range(5, 0, -1): clips.append(mp.ImageClip(draw_frame(q, opt, timer=t, head=h)).set_duration(1).set_audio(tick))
        aa = f"{audio_dir}/a{j}.mp3"; generate_audio(f"Answer is {ans}. {exp}", aa, is_exp=True)
        a_aud = mp.AudioFileClip(aa); clips.append(mp.ImageClip(draw_frame(q, opt, ans=ans, exp=exp, head=h)).set_duration(a_aud.duration + 1).set_audio(a_aud))

    out_file = "output.mp4"
    final_video = mp.concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(out_file, fps=24, codec="libx264", preset="ultrafast")

    # 📲 Send to Telegram
    with open(out_file, 'rb') as v:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={'chat_id': USER_ID, 'caption': f"✅ {topic} Video Ready!"}, files={'video': v})
    print("🚀 Video Sent!")

if __name__ == "__main__":
    main()
    
