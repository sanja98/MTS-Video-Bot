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
        print("🚀 YT Upload Success with Thumbnail!")
    except Exception as e: print(f"❌ YT Error: {e}")

def create_thumbnail(topic):
    W, H = (1280, 720)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    f_l = ImageFont.truetype(f_p, 80); f_s = ImageFont.truetype(f_p, 50)
    draw.rectangle([0, 0, W, 120], fill=(255, 193, 7))
    draw.text((50, 20), "WORLD GK CHALLENGE", fill=(0,0,0), font=f_l)
    draw.text((50, 300), topic.upper(), fill=(255, 255, 255), font=f_l)
    draw.text((50, 450), "Can you score 10/10?", fill=(0, 255, 200), font=f_s)
    img.save("thumb.jpg"); return "thumb.jpg"

def draw_frame(q, opts, timer=None, ans=None, exp=None, head="", subject="GK"):
    W, H = (1920, 1080)
    img = Image.new('RGB', (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    f_p = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    f_m = ImageFont.truetype(f_p, 50); f_s = ImageFont.truetype(f_p, 40); f_t = ImageFont.truetype(f_p, 150)

    # Header
    draw.rectangle([0, 0, W, 100], fill=(255, 193, 7))
    draw.text((60, 20), head[:70], fill=(15, 23, 42), font=f_m)
    
    # Question (Wrapped tight to avoid overlap)
    draw.text((100, 150), "\n".join(textwrap.wrap(q, 65)), fill=(255, 255, 255), font=f_m)
    
    # Options
    y = 380
    for k in ['A', 'B', 'C', 'D']:
        v = opts.get(k, "N/A")
        box_clr = (46, 204, 113) if (ans and k==ans) else (30, 41, 59)
        draw.rectangle([100, y, 1550, y+80], fill=box_clr, outline=(71, 85, 105), width=2)
        draw.text((130, y+15), f"{k}) {v}", fill=(255, 255, 255), font=f_s)
        y += 105
        
    # Timer
    if timer: 
        draw.ellipse([1620, 400, 1850, 630], outline=(255, 193, 7), width=8)
        draw.text((1690, 440), str(timer), fill=(255, 193, 7), font=f_t)

    # 🔥 FIX: Explanation Box (Upar shift kiya aur wrapping tight ki)
    if exp: 
        exp_text = "\n".join(textwrap.wrap(f"💡 Info: {exp}", 85))
        # Box positioning based on text
        draw.rectangle([100, 820, 1820, 1040], fill=(20, 30, 50), outline=(255, 193, 7), width=3)
        draw.text((130, 840), exp_text, fill=(200, 255, 200), font=f_s)

    img.save("frame.jpg"); return "frame.jpg"

# ... (Main function and other logic remains same as previous stable version)
def main():
    audio_dir = "temp_audio"
    # Load config and topic logic here...
    # (Same as before, just use the updated draw_frame)
    # At the end, call:
    # thumb = create_thumbnail(topic)
    # upload_to_youtube(video_file, viral_title, viral_desc, thumbnail_path=thumb)
