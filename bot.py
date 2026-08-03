import os
import sys
import time
import random
import warnings
import subprocess
import requests
import re
import urllib.parse
import json
from datetime import datetime, timedelta, timezone

from platform_config import get_apify_actor_config
from apify_result_parser import normalize_apify_item

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

ENABLE_STATUS_MESSAGE = True

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

needed_packages = ['yt-dlp', 'apify-client', 'gspread']
for pkg in needed_packages:
    try: __import__(pkg.replace('-', '_'))
    except ImportError: install_package(pkg)

import yt_dlp
from apify_client import ApifyClient
import gspread

try:
    from google.colab import drive, auth
    from google.auth import default
except ImportError:
    pass

from google.oauth2.service_account import Credentials

# ==========================================
# API Keys from Environment (GitHub Secrets)
# ==========================================
yt_env = os.environ.get("YOUTUBE_API_KEYS") or os.environ.get("YOUTUBE_API_KEY") or ""
YOUTUBE_API_KEYS = list(set([k.strip() for k in yt_env.split(',') if k.strip()]))

apify_env = os.environ.get("APIFY_TOKENS") or os.environ.get("APIFY_TOKEN") or ""
APIFY_TOKENS = list(set([k.strip() for k in apify_env.split(',') if k.strip()]))

SHEET_ID = os.environ.get("SHEET_ID")
CREDENTIALS_JSON = os.environ.get("CREDENTIALS_JSON")

print(f"Loaded YouTube Keys: {len(YOUTUBE_API_KEYS)} key(s)")
print(f"Loaded Apify Tokens: {len(APIFY_TOKENS)} token(s)")
if CREDENTIALS_JSON:
    print("CREDENTIALS_JSON found for Google service account")
else:
    print("No CREDENTIALS_JSON secret - Google Sheets auth not configured")

GOOGLE_CHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAQAGsvHT0c/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=_gjfX3kZs7NEU6fxNYYTvVkhZFEC7WkwfEdxZ0fvKTw"
GOOGLE_CHAT_WEBHOOK_TIKTOK = "https://chat.googleapis.com/v1/spaces/AAQAVJqrmLA/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=ou91FN0mQsnKko53YBsr3O7UEPdlaZVWgBHXeZcg5Gk"

BASE_PATH = './'
RESULTS_PATH = os.path.join(BASE_PATH, 'Results')
os.makedirs(RESULTS_PATH, exist_ok=True)
BKK_TZ = timezone(timedelta(hours=7))

DEFAULT_BUDGET_LIMIT = 3
APIFY_RATE_PER_RESULT = 0.004

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = None
try:
    if CREDENTIALS_JSON:
        credentials_dict = json.loads(CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    else:
        raise ValueError('CREDENTIALS_JSON is not set')
    gc = gspread.authorize(creds)
except Exception as e:
    print(f"[Auth Issue - Not Critical if running on Colab]: {e}")
    gc = None

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

def is_run_active(status):
    if status is None:
        return False
    status_text = str(status).strip()
    return "Start" in status_text or "green" in status_text.lower()

def send_google_chat_message(message, webhook_url):
    if not webhook_url or not webhook_url.startswith("http"): return
    try:
        res = requests.post(webhook_url, headers={"Content-Type": "application/json"}, json={"text": message})
        if res.status_code == 200:
            print("Google Chat message sent")
    except Exception as e:
        print(f"Google Chat Send Exception: {e}")

def generate_summary_message(name_group, p_list, raw, unique, dup):
    if not raw and not unique: return None
    msg = f"Scraped data from Scraper ({name_group})\n"
    msg += f"Platforms: {', '.join(p_list)}\n"
    msg += f"Fetched total: {len(raw)} posts\n"
    msg += f"New posts: {len(unique)} posts\n\n"

    if unique:
        msg += "New post links:\n"
        for u in unique[:15]:
            msg += f"  {u['url']}\n"
        if len(unique) > 15:
            msg += f"  ... and {len(unique) - 15} more\n"
        msg += "\n"

    msg += "Check details in Sheet Log"
    return msg

def update_heartbeat(ws_control):
    try:
        ws_control.update_cell(11, 2, get_bkk_now().strftime('%Y-%m-%d %H:%M:%S'))
    except:
        pass

def check_and_reset_daily_budget(ws_control, budget_limit):
    try:
        current_date = get_bkk_now()
        current_date_str = current_date.strftime('%Y-%m-%d')

        try:
            last_reset_str = ws_control.cell(12, 2).value
            last_reset_date = str(last_reset_str).strip()[:10] if last_reset_str else None
        except:
            last_reset_date = None

        if last_reset_date != current_date_str:
            ws_control.update_cell(10, 2, str(round(float(budget_limit), 4)))
            ws_control.update_cell(12, 2, current_date_str)
            print(f"Daily Budget Reset: {current_date_str} | Remaining: {budget_limit}$")
            return float(budget_limit)
    except Exception as e:
        print(f"Daily Budget Check Error: {e}")

    return None

def fetch_data(platforms, keywords, max_res, days_back, budget_remaining):
    all_videos = []
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=days_back)
    estimated_apify_cost = max_res * APIFY_RATE_PER_RESULT

    for plat in platforms:
        for kw in keywords:
            print(f"Searching '{kw}' on {plat}...")

            if plat == 'YouTube':
                success = False
                for yt_key in YOUTUBE_API_KEYS:
                    if not yt_key or "insert_" in yt_key: continue
                    try:
                        params = {'part': 'snippet', 'q': kw, 'key': yt_key, 'maxResults': max_res, 'type': 'video', 'publishedAfter': cutoff_utc.isoformat().replace('+00:00', 'Z')}
                        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params).json()

                        if 'error' in res:
                            print(f"  YouTube Key (ending ...{yt_key[-4:]}) error: {res['error']['message']}")
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
                        print(f"  YouTube Request Error (Key ...{yt_key[-4:]}): {e}")
                        continue

                if not success:
                    print(f"  All YouTube API Keys exhausted or not configured!")

            else:
                actor, inp = get_apify_actor_config(plat, kw, max_res, days_back)
                if not actor:
                    print(f"  No Apify actor configured for {plat} yet.")
                    continue

                success = False
                estimated_apify_cost = max_res * APIFY_RATE_PER_RESULT
                if budget_remaining < estimated_apify_cost:
                    print(f"  Skipping Apify for {plat} because budget remaining ({budget_remaining}$) is below estimated cost ({estimated_apify_cost}$)")
                    continue

                for apify_token in APIFY_TOKENS:
                    if not apify_token or "insert_" in apify_token: continue
                    try:
                        client = ApifyClient(apify_token)
                        try:
                            print(f"  Apify actor call: actor={actor}, keyword={kw}, input={json.dumps(inp, ensure_ascii=False)}")
                        except Exception:
                            print(f"  Apify actor call: actor={actor}, keyword={kw}, input={inp}")
                        run = client.actor(actor).call(run_input=inp, timeout_secs=120)

                        count_apify = 0
                        for item in client.dataset(run["defaultDatasetId"]).list_items().items:
                            if count_apify >= max_res: break
                            if not item or 'error' in item: continue

                            normalized = normalize_apify_item(item, plat, cutoff_utc)
                            if normalized and normalized.get('url'):
                                normalized['date'] = format_to_bkk(normalized.get('date'))
                                if plat == 'LinkedIn' and normalized.get('is_old'):
                                    continue
                                all_videos.append(normalized)
                                count_apify += 1

                        success = True
                        break
                    except Exception as e:
                        error_msg = str(e).replace('\n', ' | ')
                        print(f"  Apify Token (ending ...{apify_token[-4:]}) error: {error_msg[:150]}...")
                        continue

                if not success:
                    print(f"  All Apify Tokens exhausted or not configured for {plat}!")
                else:
                    budget_remaining -= estimated_apify_cost
                    print(f"  Deducted {estimated_apify_cost}$ for Apify call, remaining budget: {budget_remaining}$")
                    if budget_remaining < 0:
                        budget_remaining = 0.0

    return all_videos, budget_remaining

def main():
    global gc

    if not SHEET_ID and 'auth' in globals():
        auth.authenticate_user()
        creds, _ = default()
        gc = gspread.authorize(creds)
        target_sheet_id = "1RwsclzY3ssqnXSccdsclk53Lg6CJUvhKy9TMRXXgp6k"
    else:
        target_sheet_id = SHEET_ID

    if not target_sheet_id:
        print("SHEET_ID not found - check configuration")
        sys.exit(1)

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
                ws_logs.append_row(['Timestamp', 'Duplicate List', 'Unique List', 'Platforms'])
            break
        except Exception as e:
            print(f"Google Sheets connection failed (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(10)
            else:
                print("Cannot connect to Google Sheets - shutting down")
                sys.exit(1)

    scanned_memory = set()
    print(f"\nSCRAPER BOT ONLINE")

    while True:
        try:
            update_heartbeat(ws_control)
            config = ws_control.col_values(2)
            status = str(config[0]).strip() if len(config) > 0 else "Stop"

            if not is_run_active(status):
                print(f"\nStop signal detected from Control_Panel. Exiting loop.")
                break

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

            reset_budget = check_and_reset_daily_budget(ws_control, budget_limit)
            if reset_budget is not None:
                budget_remaining = reset_budget

            print(f"\n\nProcessing Batch: {get_bkk_now().strftime('%H:%M:%S')} (Max Results: {max_res}, Budget Remaining: {budget_remaining}$)")
            raw_list, budget_remaining = fetch_data(platforms, keywords, max_res, days_back, budget_remaining)
            processed_urls = set(ws_data.col_values(7)[1:])

            unique_list, duplicate_list, seen_in_run = [], [], set()

            for v in raw_list:
                if v['url'] in processed_urls or v['url'] in scanned_memory or v['url'] in seen_in_run or v.get('is_old', False):
                    duplicate_list.append(v)
                else:
                    seen_in_run.add(v['url'])
                    unique_list.append(v)

            print(f"Found: {len(raw_list)} (New: {len(unique_list)} / Dup & Old: {len(duplicate_list)})")

            new_text = "\n".join([f"[{u['platform']}] {sanitize_for_sheets(u['title'])[:50]}... -> {u['url']}" for u in unique_list])
            dup_text = "\n".join([f"[{d['platform']}] {sanitize_for_sheets(d['title'])[:50]}... -> {d['url']}" for d in duplicate_list])

            try:
                ws_logs.insert_row([get_bkk_now().strftime('%Y-%m-%d %H:%M:%S'), str(dup_text) if dup_text else "-", str(new_text) if new_text else "-", str(", ".join(platforms))], index=2)
                time.sleep(2)
            except:
                pass

            batch_rows_to_insert = []

            for v in unique_list:
                print(f"Processing: [{v['user']}] - {v['title'][:40]}...")

                clean_title = sanitize_for_sheets(v.get('title', 'No Title'))
                clean_user = sanitize_for_sheets(v.get('user', 'Unknown'))
                clean_platform = sanitize_for_sheets(v.get('platform', '-'))
                clean_date = sanitize_for_sheets(v.get('date', '-'))
                clean_url = sanitize_for_sheets(v.get('url', '-'))

                current_run_time = get_bkk_now().strftime('%Y-%m-%d %H:%M:%S')
                row_data = [
                    clean_date, clean_title, clean_platform,
                    clean_user, "-", "-",
                    clean_url, "-", "FALSE", current_run_time
                ]
                batch_rows_to_insert.append(row_data)
                scanned_memory.add(v['url'])

            if batch_rows_to_insert:
                try:
                    batch_rows_to_insert.reverse()
                    ws_data.insert_rows(batch_rows_to_insert, row=2, value_input_option='USER_ENTERED')
                    print("  All data saved to 'Apify' sheet!")
                except Exception as sheet_err:
                    print(f"  Sheet write error: {sheet_err}")

            try:
                ws_control.update_cell(10, 2, str(round(budget_remaining, 4)))
                print(f"Updated Today's Remaining Budget: {round(budget_remaining, 4)}$")
            except Exception as e:
                print(f"Failed to persist today's remaining budget: {e}")

            if ENABLE_STATUS_MESSAGE:
                msg_all = generate_summary_message("All Platforms", platforms, raw_list, unique_list, duplicate_list)
                if msg_all: send_google_chat_message(msg_all, GOOGLE_CHAT_WEBHOOK)

            tk_raw = [x for x in raw_list if x['platform'] == 'TikTok']
            tk_uni = [x for x in unique_list if x['platform'] == 'TikTok']
            tk_dup = [x for x in duplicate_list if x['platform'] == 'TikTok']
            tk_plats = ['TikTok'] if 'TikTok' in platforms else []

            if tk_plats and ENABLE_STATUS_MESSAGE:
                msg_tk = generate_summary_message("TikTok", tk_plats, tk_raw, tk_uni, tk_dup)
                if msg_tk: send_google_chat_message(msg_tk, GOOGLE_CHAT_WEBHOOK_TIKTOK)

            if 'Run Once' in run_mode:
                print("\nRun Once finished. Updating status to Stop.")
                try:
                    ws_control.update_cell(1, 2, 'Stop')
                except:
                    pass
                if not ('auth' in globals()):
                    break

            if not ('auth' in globals()):
                print("\nServerless Mode finished 1 cycle. Keeping status Active for next Watchdog trigger.")
                break
            else:
                if 'Run Once' not in run_mode:
                    interval = int(config[5]) if str(config[5]).isdigit() else 60
                    print(f"\nNext iteration in {interval} mins...")
                    for _ in range(interval * 6):
                        update_heartbeat(ws_control)
                        time.sleep(10)

        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
