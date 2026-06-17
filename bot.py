# -*- coding: utf-8 -*-
"""
🚀 INTELLIGENT LOGO HUNTER v8.2.1 (Ultimate GitHub Edition - Stable Restore)
- โค้ดรุ่นเสถียรรักษาโครงสร้าง v7.9.1 ดั้งเดิม 100% เชื่อมต่อ Secrets บัญชีใหม่ปลอดภัย
- 🛠️ แก้ปัญหาภาพหลักฐานไม่ขึ้น (-) ด้วยระบบฝากรูปฟรีสำรองอัตโนมัติ (Catbox & Tmpfiles) เมื่อ Google Drive พื้นที่เต็ม
- ใช้การค้นหาผ่าน 'clockworks/tiktok-scraper' ดึงค่าตัวแปรจากแถวเดิมคงที่ (B1 - B7)
- ระบบ Hard Limit ป้องกันการดึงคลิปเกินจำนวนที่กำหนด (ประหยัดทรัพยากรเครื่อง)
- เพิ่มระบบ Retry ป้องกัน Google Sheets API Error 503 ล่มชั่วคราว
- อ่านค่า Time Filter แบบเดิม (1=Day, 2=Week, 3=Month)
- เก็บ Log คลิปเก่ารวมในลิสต์ "ซ้ำ" แต่ไม่สแกนและไม่ลง Sheet Apify
- Batch Insert แทรก "FALSE" ให้ Checkbox ใช้งานได้ (คอลัมน์ I), Timestamp (คอลัมน์ J)
"""

import os
import sys
import time
import random
import warnings
import subprocess
import requests
import re
import numpy as np
import urllib.parse
import base64
import io
import json
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

ENABLE_STATUS_MESSAGE = True

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

needed_packages = ['yt-dlp', 'apify-client', 'gspread', 'opencv-python', 'torch', 'torchvision']
for pkg in needed_packages:
    try: __import__(pkg.replace('-', '_'))
    except ImportError: install_package(pkg)

import yt_dlp
from apify_client import ApifyClient
import cv2
import torch
import gspread
from PIL import Image
from torchvision import transforms

# 🛡️ ป้องกัน Error เวลาไม่ได้รันบน Colab
try:
    from google.colab import drive, auth
    from google.auth import default
except ImportError:
    pass 

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 🔑 ดึง API Keys จาก Environment (GitHub Secrets)
# ==========================================
yt_env = os.environ.get("YOUTUBE_API_KEYS") or os.environ.get("YOUTUBE_API_KEY") or ""
YOUTUBE_API_KEYS = list(set([k.strip() for k in yt_env.split(',') if k.strip()]))

apify_env = os.environ.get("APIFY_TOKENS") or os.environ.get("APIFY_TOKEN") or ""
APIFY_TOKENS = list(set([k.strip() for k in apify_env.split(',') if k.strip()]))

SHEET_ID = os.environ.get("SHEET_ID")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
CREDENTIALS_JSON = os.environ.get("CREDENTIALS_JSON")

print(f"โหลด YouTube Keys: {len(YOUTUBE_API_KEYS)} ตัว")
print(f"โหลด Apify Tokens: {len(APIFY_TOKENS)} ตัว")
if IMGBB_API_KEY:
    print("✅ ตรวจพบ IMGBB_API_KEY จะใช้ระบบฝากรูป ImgBB แทน Google Drive")
if CREDENTIALS_JSON:
    print("✅ ตรวจพบ CREDENTIALS_JSON สำหรับ Google service account")
else:
    print("⚠️ ไม่มี CREDENTIALS_JSON secret ตรวจสอบการตั้งค่า Google Sheets/Drive")

# 🔴 WEBHOOK URL
GOOGLE_CHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAGsvHT0c/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=_gjfX3kZs7NEU6fxNYYTvVkhZFEC7WkwfEdxZ0fvKTw"
GOOGLE_CHAT_WEBHOOK_TIKTOK = "https://chat.googleapis.com/v1/spaces/AAQAtSkMPnY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=WhACImSKOnMpTU-3iyj92I-y6xmDd3KDHZtVY7GehNQ"

BASE_PATH = './'
RESULTS_PATH = os.path.join(BASE_PATH, 'Results')
os.makedirs(RESULTS_PATH, exist_ok=True)
MODEL_PATH = os.path.join(BASE_PATH, 'bigc_model.pth')
BKK_TZ = timezone(timedelta(hours=7))
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DEFAULT_BUDGET_LIMIT = 3
APIFY_RATE_PER_RESULT = 0.004

# --- Authentication (Sheet & Drive) ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = None
try:
    if CREDENTIALS_JSON:
        credentials_dict = json.loads(CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    else:
        raise ValueError('CREDENTIALS_JSON is not set')
    gc = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    print(f"⚠️ [Auth Issue - Not Critical if running on Colab]: {e}")
    gc = None
    drive_service = None

def get_bkk_now(): 
    return datetime.now(BKK_TZ)

def format_to_bkk(date_input):
    try:
        if isinstance(date_input, str) and date_input.replace('.', '', 1).isdigit():
            date_input = float(date_input)
        if isinstance(date_input, (int, float)):
            val = date_input if date_input < 1e11 else date_input / 1000.0
            dt = datetime.fromtimestamp(val, timezone.utc)
        else:
            clean_str = str(date_input).replace('Z', '+00:00').replace("'", "").strip()
            dt = datetime.fromisoformat(clean_str[:19] + '+00:00')
        return dt.astimezone(BKK_TZ).strftime('%Y-%m-%d %H:%M:%S')
    except: 
        return str(date_input).replace("'", "").strip()

def sanitize_for_sheets(text):
    if not text: return "-"
    clean_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', str(text))
    clean_text = clean_text.replace('\n', ' ').strip()
    if clean_text.startswith(('=', '+', '-', '@')):
        clean_text = f"'{clean_text}"
    return clean_text[:2500]

def send_google_chat_message(message, webhook_url):
    if not webhook_url or not webhook_url.startswith("http"): return
    try:
        res = requests.post(webhook_url, headers={"Content-Type": "application/json"}, json={"text": message})
        if res.status_code == 200: 
            print("✅ ส่ง Google Chat สำเร็จ!")
    except Exception as e: 
        print(f"⚠️ Google Chat Send Exception: {e}")

# 🛠️ ปรับฟังก์ชันแสดงข้อความรายงานให้สั้น กระชับ คลีนตา ตามเทมเพลตที่คุณต้องการ 100%
def generate_summary_message(name_group, p_list, raw, unique, dup, chat):
    if not raw and not unique: return None 
    msg = f"📊 อัปเดตข้อมูลจาก Logo Hunter ({name_group})\n"
    msg += f"🔗 แพลตฟอร์ม: {', '.join(p_list)}\n"
    msg += f"📥 ดึงมาทั้งหมด: {len(raw)} โพสต์\n"
    msg += f"✨ ข้อมูลใหม่: {len(unique)} โพสต์\n"
    msg += f"🎯 พบโลโก้: {len(chat)} โพสต์\n\n"
    
    if chat:
        msg += "🚨 ลิงก์โพสต์ที่พบโลโก้:\n"
        for item in chat[:15]: 
            msg += f"• {item['url']}\n"
            if 'img_url' in item and item['img_url'] != "-":
                msg += f"  (🖼️ รูปหลักฐาน: {item['img_url']})\n"
        if len(chat) > 15: 
            msg += f"• ... และอื่นๆ อีก {len(chat) - 15} รายการ\n"
        msg += "\n"
    elif unique:
        msg += "📌 ลิงก์โพสต์ใหม่ (ส่งตรวจสอบแล้ว):\n"
        for u in unique[:15]: 
            msg += f"• {u['url']}\n"
        if len(unique) > 15: 
            msg += f"• ... และอื่นๆ อีก {len(unique) - 15} รายการ\n"
        msg += "\n"
            
    msg += "✅ ตรวจสอบรายละเอียดได้ใน Sheet Log"
    return msg

def update_heartbeat(ws_control):
    try: 
        ws_control.update_cell(11, 2, get_bkk_now().strftime('%Y-%m-%d %H:%M:%S'))
    except: 
        pass

def check_and_reset_monthly_budget(ws_control, budget_limit):
    """
    Reset remaining budget to limit at the start of each month.
    Stores the last reset date in Control_Panel B12.
    """
    try:
        current_date = get_bkk_now()
        current_month = current_date.strftime('%Y-%m')
        
        # Read last reset date from B11
        try:
            last_reset_str = ws_control.cell(11, 2).value
            last_reset_month = last_reset_str.split('-')[0:2] if last_reset_str else None
            last_reset_month = '-'.join(last_reset_month) if last_reset_month else None
        except:
            last_reset_month = None
        
        # If month changed or never reset, reset the budget
        if last_reset_month != current_month:
            ws_control.update_cell(10, 2, str(round(float(budget_limit), 4)))
            ws_control.update_cell(11, 2, current_date.strftime('%Y-%m-%d'))
            print(f"✅ Monthly Budget Reset: {current_month} | Remaining: {budget_limit}$")
            return float(budget_limit)
    except Exception as e:
        print(f"⚠️ Monthly Budget Check Error: {e}")
    
    return None

def load_ai_model():
    if os.path.exists(MODEL_PATH):
        try:
            m = torch.load(MODEL_PATH, map_location=device, weights_only=False)
            if hasattr(m, 'eval'): m.eval()
            print("🧠 AI Model Engine: ONLINE")
            return m
        except: 
            pass
    print("⚠️ Model not found. Skipping video analysis.")
    return None

def predict_logo(model, frame):
    if model is None: return False, 0.0, None
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cv2.resize(rgb, (224, 224)))
        transform = transforms.Compose([
            transforms.Resize((224, 224)), transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        with torch.no_grad():
            output = model(transform(pil_img).unsqueeze(0).to(device))
            prob = torch.nn.functional.softmax(output[0], dim=0)
            conf, pred = torch.max(prob, 0)
        if pred.item() == 0 and conf.item() > 0.85: 
            return True, conf.item(), Image.fromarray(rgb)
    except: 
        pass
    return False, 0.0, None

def save_evidence(image_pil, video_id, timestamp_str):
    local_filename = "-"
    try:
        safe_ts = str(timestamp_str).replace(":", "_")
        local_filename = f"DETECT_{video_id}_{safe_ts}.jpg"
        
        # 🌟 1. ลองอัปโหลดผ่าน ImgBB ก่อน (หากคุณตั้งค่าไว้ใน GitHub Secrets)
        if IMGBB_API_KEY:
            try:
                buffered = io.BytesIO()
                image_pil.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                payload = {
                    "key": IMGBB_API_KEY,
                    "image": img_str,
                    "name": local_filename
                }
                res = requests.post("https://api.imgbb.com/1/upload", data=payload)
                if res.status_code == 200:
                    img_url = res.json()["data"]["url"]
                    return f'=HYPERLINK("{img_url}", "🖼️ กดดูรูปภาพ")', img_url
                else:
                    print(f" ⚠️ ImgBB Upload Error: {res.text}")
            except Exception as imgbb_e:
                print(f" ⚠️ ImgBB Exception: {imgbb_e}")

        # 🌟 2. ลองอัปโหลดผ่าน Google Drive (หากแชร์สิทธิ์เป็น Editor ไว้)
        try:
            image_pil.save(local_filename)
            if GDRIVE_FOLDER_ID and ('drive_service' in globals()):
                file_metadata = {'name': local_filename, 'parents': [GDRIVE_FOLDER_ID]}
                media = MediaFileUpload(local_filename, mimetype='image/jpeg', resumable=True)
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
                url = file.get('webViewLink')
                if os.path.exists(local_filename):
                    os.remove(local_filename)
                return f'=HYPERLINK("{url}", "🖼️ กดดูรูปภาพ")', url
        except Exception as drive_e:
            print(f" ⚠️ Google Drive Upload Failed (Quota/Auth Issue): {drive_e}")

        # 🌟 3. 🚨 ระบบสำรองอัจฉริยะแบบไร้ตัวตน (Catbox & Tmpfiles Fallback)
        # หากทั้ง Google Drive และ ImgBB ติดปัญหาด้านสิทธิ์หรือโควตา บอทจะอัปโหลดรูปฝากไว้ที่นี่ให้อัตโนมัติเพื่อให้ลิงก์แสดงผลได้เสมอตลอด 24 ชั่วโมง
        for service in ['catbox', 'tmpfiles']:
            try:
                buffered = io.BytesIO()
                image_pil.save(buffered, format="JPEG")
                buffered.seek(0)
                
                if service == 'catbox':
                    res = requests.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": (local_filename, buffered, "image/jpeg")},
                        timeout=15
                    )
                    if res.status_code == 200 and res.text.startswith("http"):
                        img_url = res.text.strip()
                        print(f" 🟢 [Fallback Success] อัปโหลดรูปสำเร็จผ่าน Catbox: {img_url}")
                        if os.path.exists(local_filename):
                            os.remove(local_filename)
                        return f'=HYPERLINK("{img_url}", "🖼️ กดดูรูปภาพ")', img_url
                        
                elif service == 'tmpfiles':
                    res = requests.post(
                        "https://tmpfiles.org/api/v1/upload",
                        files={"file": (local_filename, buffered, "image/jpeg")},
                        timeout=15
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") == "success":
                            orig_url = data["data"]["url"]
                            img_url = orig_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                            print(f" 🟢 [Fallback Success] อัปโหลดรูปสำเร็จผ่าน Tmpfiles: {img_url}")
                            if os.path.exists(local_filename):
                                os.remove(local_filename)
                            return f'=HYPERLINK("{img_url}", "🖼️ กดดูรูปภาพ")', img_url
            except Exception as fb_e:
                print(f" ⚠️ Fallback to {service} failed: {fb_e}")

        if os.path.exists(local_filename):
            os.remove(local_filename)
        return "-", "-"
    except Exception as e:
        print(f" ⚠️ Save Evidence Exception: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return "-", "-"

def fetch_data(platforms, keywords, max_res, days_back, budget_remaining):
    all_videos = []
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=days_back)
    estimated_apify_cost = max_res * APIFY_RATE_PER_RESULT
    
    for plat in platforms:
        for kw in keywords:
            print(f"📡 Searching '{kw}' on {plat}...")
            
            if plat == 'YouTube':
                success = False
                for yt_key in YOUTUBE_API_KEYS:
                    if not yt_key or "ใส่_" in yt_key: continue
                    try:
                        params = {'part': 'snippet', 'q': kw, 'key': yt_key, 'maxResults': max_res, 'type': 'video', 'publishedAfter': cutoff_utc.isoformat().replace('+00:00', 'Z')}
                        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params).json()
                        
                        if 'error' in res:
                            print(f"  ⚠️ YouTube Key (ลงท้าย {yt_key[-4:]}) มีปัญหา: {res['error']['message']}")
                            continue
                            
                        count_yt = 0
                        for item in res.get('items', []):
                            if count_yt >= max_res: break
                            all_videos.append({
                                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}", 
                                'title': item['snippet']['title'], 
                                'platform': 'YouTube', 
                                'user': item['snippet']['channelTitle'], 
                                'date': format_to_bkk(item['snippet']['publishedAt']), 
                                'image_url': item['snippet']['thumbnails']['high']['url'], 
                                'id': item['id']['videoId'],
                                'is_old': False 
                            })
                            count_yt += 1
                        
                        success = True
                        break 
                    except Exception as e:
                        print(f"  ⚠️ YouTube Request Error (Key ...{yt_key[-4:]}): {e}")
                        continue
                
                if not success:
                    print(f"  ❌ YouTube API Keys ทั้งหมดโควตาเต็ม หรือไม่ได้ตั้งค่า!")

            else:
                actor = {'TikTok': 'clockworks/tiktok-scraper', 'Instagram': 'apify/instagram-hashtag-scraper', 'Facebook': 'apify/facebook-search-scraper'}.get(plat)
                if not actor: continue
                
                inp = {}
                if plat == 'TikTok':
                    clean_kw = kw.replace("#", "").strip()
                    inp = {
                        "maxItems": max_res,
                        "resultsPerPage": max_res,
                        "proxyConfiguration": {"useApifyProxy": True}
                    }
                    if kw.startswith('#'):
                        inp["hashtags"] = [clean_kw]
                    else:
                        inp["searchQueries"] = [kw]
                elif plat == 'Instagram':
                    inp = {
                        "hashtags": [kw.replace("#", "").replace(" ", "")],
                        "resultsLimit": max_res,
                        "proxyConfiguration": {"useApifyProxy": True}
                    }
                elif plat == 'Facebook':
                    inp = {
                        "searchTerms": kw,
                        "resultsLimit": max_res,
                        "maxItems": max_res,
                        "proxyConfiguration": {"useApifyProxy": True}
                    }
                
                success = False
                estimated_apify_cost = max_res * APIFY_RATE_PER_RESULT
                if budget_remaining < estimated_apify_cost:
                    print(f"  ⛔ Skipping Apify for {plat} because budget remaining ({budget_remaining}$) is below estimated cost ({estimated_apify_cost}$)")
                    continue

                for apify_token in APIFY_TOKENS:
                    if not apify_token or "ใส่_" in apify_token: continue
                    try:
                        client = ApifyClient(apify_token)
                        run = client.actor(actor).call(run_input=inp, timeout_secs=120)
                        
                        count_apify = 0
                        for item in client.dataset(run["defaultDatasetId"]).list_items().items:
                            if count_apify >= max_res: break
                            if not item or 'error' in item: continue

                            raw_date = item.get('createTime') or item.get('createdAt') or item.get('timestamp') or item.get('date') or item.get('create_time')
                            is_old = False
                            try:
                                if raw_date:
                                    rd = float(raw_date) if isinstance(raw_date, str) and raw_date.replace('.', '', 1).isdigit() else raw_date
                                    if isinstance(rd, (int, float)):
                                        dt_utc = datetime.fromtimestamp(rd if rd < 1e11 else rd/1000.0, timezone.utc)
                                    else:
                                        clean_str = str(rd).replace('Z', '+00:00')[:19] + '+00:00'
                                        dt_utc = datetime.fromisoformat(clean_str)
                                    
                                    if dt_utc < cutoff_utc:
                                        is_old = True
                            except: 
                                pass
                            
                            user = "Unknown"
                            if isinstance(item.get('authorMeta'), dict): user = item['authorMeta'].get('name') or item['authorMeta'].get('nickName') or "Unknown"
                            elif isinstance(item.get('author'), dict): user = item['author'].get('uniqueId') or item['author'].get('nickname') or "Unknown"
                            elif isinstance(item.get('author'), str): user = item['author']
                            if user == "Unknown" or not user: user = item.get('authorNickname') or item.get('authorName') or item.get('ownerUsername') or item.get('author_id') or "Unknown"
                                
                            title_raw = item.get('caption') or item.get('text') or item.get('desc') or item.get('title') or item.get('video_description') or "No Title"
                            if isinstance(title_raw, dict): title_raw = title_raw.get('text', 'No Title')
                            title = str(title_raw)
                            
                            item_id = item.get('id') or item.get('video', {}).get('id') or item.get('video_id')
                            if not item_id: item_id = str(random.randint(10000, 99999))
                            
                            v_url = item.get('webVideoUrl') or item.get('videoWebUrl') or item.get('url') or item.get('postUrl') or item.get('video_url')
                            if not v_url and plat == 'TikTok': v_url = f"https://www.tiktok.com/@{user}/video/{item_id}"
                            
                            image_url = item.get('displayUrl') or item.get('imageUrl') or item.get('coverUrl') or item.get('video', {}).get('cover') or item.get('origin_cover') or item.get('videoMeta', {}).get('coverUrl')

                            if v_url:
                                all_videos.append({
                                    'url': str(v_url), 'title': str(title)[:200], 'platform': str(plat), 'user': str(user), 
                                    'date': format_to_bkk(raw_date), 'id': str(item_id), 'image_url': str(image_url) if image_url else None,
                                    'is_old': is_old 
                                })
                                count_apify += 1
                        
                        success = True
                        break 
                    except Exception as e:
                        error_msg = str(e).replace('\n', ' | ')
                        print(f"  ⚠️ Apify Token (ลงท้าย ...{apify_token[-4:]}) ติดปัญหา: {error_msg[:150]}...")
                        continue

                if not success:
                    print(f"  ❌ Apify Tokens ทั้งหมดเครดิตหมด หรือไม่ได้ตั้งค่าสำหรับ {plat}!")
                else:
                    budget_remaining -= estimated_apify_cost
                    print(f"  ✅ Deducted {estimated_apify_cost}$ for Apify call, remaining budget: {budget_remaining}$")
                    if budget_remaining < 0:
                        budget_remaining = 0.0
                    # continue with next platform or keyword once budget updated
                
    return all_videos, budget_remaining

def main():
    global gc
    
    # เลือกว่าจะ Auth แบบ Colab หรือแบบ GitHub Secrets
    if not SHEET_ID and 'auth' in globals():
        auth.authenticate_user()
        creds, _ = default()
        gc = gspread.authorize(creds)
        target_sheet_id = "1RwsclzY3ssqnXSccdsclk53Lg6CJUvhKy9TMRXXgp6k" 
    else:
        target_sheet_id = SHEET_ID

    if not target_sheet_id:
        print("❌ ไม่พบ SHEET_ID กรุณาตรวจสอบการตั้งค่า")
        sys.exit(1)

    # 🛡️ เพิ่มระบบ Retry ป้องกัน Google Sheets API ล่มชั่วคราว (Error 503)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sh = gc.open_by_key(target_sheet_id)
            ws_data = sh.worksheet("Apify")
            ws_control = sh.worksheet("Control_Panel")
            try: 
                ws_logs = sh.worksheet("Scan_Logs")
            except:
                ws_logs = sh.add_worksheet(title="Scan_Logs", rows=1000, cols=4)
                ws_logs.append_row(['Timestamp', 'ลิสต์รายการที่ซ้ำ', 'ลิสต์รายการที่ไม่ซ้ำ', 'Platforms'])
            break # สำเร็จแล้วออกจากลูป
        except Exception as e:
            print(f"⚠️ การเชื่อมต่อ Google Sheets ขัดข้อง (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(10) # รอ 10 วินาทีแล้วลองใหม่
            else:
                print("❌ ไม่สามารถเชื่อมต่อ Google Sheets ได้ ระบบจะปิดการทำงานเพื่อความปลอดภัย")
                sys.exit(1)

    engine = load_ai_model()
    scanned_memory = set()
    print(f"\n🚀 LOGO HUNTER v8.2.1 (GitHub Edition) ONLINE")

    while True:
        try:
            update_heartbeat(ws_control)
            config = ws_control.col_values(2)
            status = str(config[0]).strip() if len(config) > 0 else "🔴 Stop"

            if 'Start' not in status and '🟢' not in status:
                print(f"\r⏳ [Standby] Waiting for command... ({get_bkk_now().strftime('%H:%M:%S')})", end="")
                time.sleep(15)
                continue

            platforms = [p.strip() for p in config[1].split(',')]
            keywords = [k.strip() for k in config[2].split(',')]
            
            days_back = 1 if '1' in str(config[3]) else 7 if '2' in str(config[3]) else 30
            max_res = int(config[6]) if str(config[6]).isdigit() else 5
            run_mode = str(config[4]).strip()

            try:
                budget_limit = float(config[7]) if len(config) > 7 and str(config[7]).strip() else DEFAULT_BUDGET_LIMIT
            except (ValueError, TypeError):
                budget_limit = DEFAULT_BUDGET_LIMIT

            try:
                budget_remaining = float(config[8]) if len(config) > 8 and str(config[8]).strip() else float(budget_limit)
            except:
                budget_remaining = float(budget_limit)

            # Check if we need to reset budget at start of month
            reset_budget = check_and_reset_monthly_budget(ws_control, budget_limit)
            if reset_budget is not None:
                budget_remaining = reset_budget

            print(f"\n\n🔥 Processing Batch: {get_bkk_now().strftime('%H:%M:%S')} (Max Results: {max_res}, Budget Remaining: {budget_remaining}$)")
            raw_list, budget_remaining = fetch_data(platforms, keywords, max_res, days_back, budget_remaining)
            processed_urls = set(ws_data.col_values(7)[1:]) 
            
            unique_list, duplicate_list, seen_in_run = [], [], set()
            
            for v in raw_list:
                if v['url'] in processed_urls or v['url'] in scanned_memory or v['url'] in seen_in_run or v.get('is_old', False): 
                    duplicate_list.append(v)
                else: 
                    seen_in_run.add(v['url'])
                    unique_list.append(v)
                    
            print(f"📋 Found: {len(raw_list)} (New: {len(unique_list)} / Dup & Old: {len(duplicate_list)})")
            
            new_text = "\n".join([f"[{u['platform']}] {sanitize_for_sheets(u['title'])[:50]}... -> {u['url']}" for u in unique_list])
            dup_text = "\n".join([f"[{d['platform']}] {sanitize_for_sheets(d['title'])[:50]}... -> {d['url']}" for d in duplicate_list])

            try: 
                ws_logs.insert_row([get_bkk_now().strftime('%Y-%m-%d %H:%M:%S'), str(dup_text) if dup_text else "-", str(new_text) if new_text else "-", str(", ".join(platforms))], index=2)
                time.sleep(2)
            except: 
                pass

            chat_summary = []
            batch_rows_to_insert = []

            if engine is None: 
                send_google_chat_message("🚨 [System Error] ไม่พบไฟล์โมเดล AI กรุณาตรวจสอบ Google Drive", GOOGLE_CHAT_WEBHOOK)

            for v in unique_list:
                print(f"👁️ Scanning: [{v['user']}] - {v['title'][:40]}...")
                found, final_ts, best_img = False, "-", None
                
                if engine is not None:
                    try:
                        with yt_dlp.YoutubeDL({'format': 'best', 'quiet': True, 'nocheckcertificate': True, 'socket_timeout': 10}) as ydl:
                            stream = ydl.extract_info(v['url'], download=False).get('url')
                            if stream:
                                cap = cv2.VideoCapture(stream)
                                for i in range(150): 
                                    ret, frame = cap.read()
                                    if not ret: break
                                    if i % 30 == 0:
                                        hit, sc, img = predict_logo(engine, frame)
                                        if hit:
                                            found, best_img, final_ts = True, img, f"{int((i//30)//60):02d}:{int((i//30)%60):02d}"
                                            break
                                cap.release()
                    except: 
                        pass

                    if not found and v.get('image_url'):
                        try:
                            resp = requests.get(v['image_url'], timeout=10)
                            img = cv2.imdecode(np.asarray(bytearray(resp.content), dtype=np.uint8), cv2.IMREAD_COLOR)
                            hit, sc, img_res = predict_logo(engine, img)
                            if hit: 
                                found, best_img, final_ts = True, img_res, "Image"
                        except: 
                            pass

                clean_title = sanitize_for_sheets(v.get('title', 'No Title'))
                clean_user = sanitize_for_sheets(v.get('user', 'Unknown'))
                clean_platform = sanitize_for_sheets(v.get('platform', '-'))
                clean_date = sanitize_for_sheets(v.get('date', '-'))
                clean_url = sanitize_for_sheets(v.get('url', '-'))
                
                if found:
                    print(f"  🎯 Logo Found at {final_ts}!")
                    formula, img_url = save_evidence(best_img, v['id'], final_ts)
                    detect_status = "Yes"
                    chat_summary.append({
                        'url': clean_url, 
                        'img_url': str(img_url), 
                        'platform': clean_platform,
                        'title': clean_title,
                        'user': clean_user
                    })
                else:
                    print("  ❌ No logo.")
                    formula, img_url = "-", "-"
                    detect_status = "No"

                current_run_time = get_bkk_now().strftime('%Y-%m-%d %H:%M:%S')
                row_data = [
                    clean_date, clean_title, clean_platform,
                    clean_user, str(detect_status), str(final_ts),
                    clean_url, str(formula), "FALSE", current_run_time 
                ]
                batch_rows_to_insert.append(row_data)
                scanned_memory.add(v['url'])

            if batch_rows_to_insert:
                try:
                    batch_rows_to_insert.reverse() 
                    ws_data.insert_rows(batch_rows_to_insert, row=2, value_input_option='USER_ENTERED')
                    print("  ✅ บันทึกลง Sheet 'Apify' สำเร็จทั้งหมด!")
                except Exception as sheet_err:
                    print(f"  ❌ เขียนลง Sheet ไม่สำเร็จ: {sheet_err}")

            try:
                ws_control.update_cell(10, 2, str(round(budget_remaining, 4)))
                print(f"🔄 Updated Today's Remaining Budget: {round(budget_remaining, 4)}$")
            except Exception as e:
                print(f"⚠️ Failed to persist today's remaining budget: {e}")

            if ENABLE_STATUS_MESSAGE or len(chat_summary) > 0:
                msg_all = generate_summary_message("รวมทุกแพลตฟอร์ม", platforms, raw_list, unique_list, duplicate_list, chat_summary)
                if msg_all: send_google_chat_message(msg_all, GOOGLE_CHAT_WEBHOOK)

            tk_raw = [x for x in raw_list if x['platform'] == 'TikTok']
            tk_uni = [x for x in unique_list if x['platform'] == 'TikTok']
            tk_dup = [x for x in duplicate_list if x['platform'] == 'TikTok']
            tk_chat = [x for x in chat_summary if x['platform'] == 'TikTok']
            tk_plats = ['TikTok'] if 'TikTok' in platforms else []

            if tk_plats and (ENABLE_STATUS_MESSAGE or len(tk_chat) > 0):
                msg_tk = generate_summary_message("TikTok", tk_plats, tk_raw, tk_uni, tk_dup, tk_chat)
                if msg_tk: send_google_chat_message(msg_tk, GOOGLE_CHAT_WEBHOOK_TIKTOK)

            # 🛠️ ปรับให้รองรับการรันแบบ Serverless (GitHub) และ Colab อย่างสมบูรณ์
            if 'Run Once' in run_mode:
                print("\n🏁 Run Once finished. Updating status to Stop.")
                try: 
                    ws_control.update_cell(1, 2, '🔴 Stop') 
                except: 
                    pass
                if not ('auth' in globals()): 
                    break # ออกจากลูปสำหรับ GitHub
            
            if not ('auth' in globals()):
                # ถ้ารันบน GitHub แบบปกติ ให้ทำงาน 1 รอบแล้วปิดตัวเอง (ให้ Watchdog มาปลุกใหม่ ไม่ต้องตั้ง Stop)
                print("\n🏁 Serverless Mode finished 1 cycle. Keeping status Active for next Watchdog trigger.")
                break 
            else:
                # ถ้ารันบน Colab แบบปกติ ให้รันวนลูปตามเวลาที่ตั้งไว้
                if 'Run Once' not in run_mode:
                    interval = int(config[5]) if str(config[5]).isdigit() else 60
                    print(f"\n💤 Next iteration in {interval} mins...")
                    for _ in range(interval * 6):
                        update_heartbeat(ws_control)
                        time.sleep(10)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
