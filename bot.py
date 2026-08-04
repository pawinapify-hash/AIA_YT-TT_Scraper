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
from status_control import is_run_active

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
APIFY_RATE_PER_RESULT = {
    'LinkedIn':  0.002,
    'TikTok':    0.004,
    'Instagram': 0.004,
    'Facebook':  0.004,
}

CFG_RANGE = 'B1:F13'
PLATFORM_COL_INDEX = {
    'Facebook':  2,
    'Instagram': 3,
    'YouTube':   4,
    'TikTok':    5,
    'LinkedIn':  6,
}
ROW_STATUS          = 5
ROW_KEYWORDS        = 6
ROW_TIME_FILTER     = 7
ROW_INTERVAL        = 8
ROW_MAX_RESULTS     = 9
ROW_BUDGET          = 10
ROW_REMAINING       = 11
ROW_LAST_EXECUTION  = 13

CELL_SYS_STATUS     = 'B1'
CELL_OVERALL_BUDGET = 'B2'
CELL_OVERALL_REMAIN = 'B3'
CELL_LAST_RESET     = 'B12'

TIME_FILTER_MAP = {1: 1, 2: 7, 3: 30}

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

def read_platform_configs(ws_control):
    cells = ws_control.range(CFG_RANGE)
    grid = {}
    for c in cells:
        grid[(c.row, c.col)] = c.value

    global_cfg = {}
    global_cfg['status'] = str(grid.get((1, 2), '') or '').strip()

    raw_budget = grid.get((2, 2))
    try:
        global_cfg['overall_budget'] = float(raw_budget) if raw_budget not in (None, '') else float(DEFAULT_BUDGET_LIMIT)
    except (ValueError, TypeError):
        global_cfg['overall_budget'] = float(DEFAULT_BUDGET_LIMIT)

    raw_remain = grid.get((3, 2))
    try:
        global_cfg['overall_remaining'] = float(raw_remain) if raw_remain not in (None, '') else global_cfg['overall_budget']
    except (ValueError, TypeError):
        global_cfg['overall_remaining'] = global_cfg['overall_budget']

    global_cfg['last_reset_date'] = str(grid.get((12, 2), '') or '').strip()

    platform_configs = {}
    for plat_name, col_num in PLATFORM_COL_INDEX.items():
        status_val = str(grid.get((ROW_STATUS, col_num), '') or '').strip()
        if not is_run_active(status_val):
            continue

        cfg = {'name': plat_name, 'col_num': col_num}

        kw_raw = grid.get((ROW_KEYWORDS, col_num))
        cfg['keywords'] = [k.strip() for k in str(kw_raw).split(',') if k.strip()] if kw_raw else []

        time_val = grid.get((ROW_TIME_FILTER, col_num))
        try:
            time_val_int = int(time_val) if time_val not in (None, '') else 3
            cfg['days_back'] = TIME_FILTER_MAP.get(time_val_int, 30)
        except (ValueError, TypeError):
            cfg['days_back'] = 30

        max_res_val = grid.get((ROW_MAX_RESULTS, col_num))
        try:
            cfg['max_results'] = int(max_res_val) if max_res_val not in (None, '') else 5
        except (ValueError, TypeError):
            cfg['max_results'] = 5

        budget_val = grid.get((ROW_BUDGET, col_num))
        try:
            cfg['budget_cap'] = float(budget_val) if budget_val not in (None, '') else global_cfg['overall_budget']
        except (ValueError, TypeError):
            cfg['budget_cap'] = global_cfg['overall_budget']

        remain_val = grid.get((ROW_REMAINING, col_num))
        try:
            cfg['budget_remaining'] = float(remain_val) if remain_val not in (None, '') else cfg['budget_cap']
        except (ValueError, TypeError):
            cfg['budget_remaining'] = cfg['budget_cap']

        interval_val = grid.get((ROW_INTERVAL, col_num))
        try:
            cfg['interval_min'] = max(int(interval_val) - 1, 1) if interval_val not in (None, '') else 60
        except (ValueError, TypeError):
            cfg['interval_min'] = 60

        last_exec_val = grid.get((ROW_LAST_EXECUTION, col_num))
        cfg['last_execution'] = None
        if last_exec_val:
            try:
                cfg['last_execution'] = datetime.strptime(str(last_exec_val).strip()[:19], '%Y-%m-%d %H:%M:%S')
                cfg['last_execution'] = cfg['last_execution'].replace(tzinfo=BKK_TZ)
            except (ValueError, TypeError):
                pass

        platform_configs[plat_name] = cfg

    return global_cfg, platform_configs

def check_and_reset_daily_budget(ws_control, global_cfg, platform_configs):
    try:
        current_date = get_bkk_now()
        current_date_str = current_date.strftime('%Y-%m-%d')

        last_reset_date = global_cfg.get('last_reset_date', '')
        last_reset_date = last_reset_date[:10] if last_reset_date else None

        if last_reset_date != current_date_str:
            global_cfg['overall_remaining'] = global_cfg['overall_budget']
            ws_control.update_cell(3, 2, str(round(global_cfg['overall_remaining'], 4)))
            for _plat_name, cfg in platform_configs.items():
                cfg['budget_remaining'] = cfg['budget_cap']
                ws_control.update_cell(ROW_REMAINING, cfg['col_num'], str(round(cfg['budget_remaining'], 4)))
            ws_control.update_cell(12, 2, current_date_str)
            global_cfg['last_reset_date'] = current_date_str
            print(f"Daily Budget Reset: {current_date_str} | Overall: {global_cfg['overall_remaining']}$")
            return global_cfg, platform_configs
    except Exception as e:
        print(f"Daily Budget Check Error: {e}")

    return None

def fetch_data(plat_name, keywords, max_results, days_back, plat_budget_remaining, overall_remaining):
    all_videos = []
    cutoff_utc = datetime.now(timezone.utc) - timedelta(days=days_back)

    for kw in keywords:
        print(f"Searching '{kw}' on {plat_name}...")

        if plat_name == 'YouTube':
            success = False
            for yt_key in YOUTUBE_API_KEYS:
                if not yt_key or "insert_" in yt_key: continue
                try:
                    params = {'part': 'snippet', 'q': kw, 'key': yt_key, 'maxResults': max_results, 'type': 'video', 'publishedAfter': cutoff_utc.isoformat().replace('+00:00', 'Z')}
                    res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params).json()

                    if 'error' in res:
                        print(f"  YouTube Key (ending ...{yt_key[-4:]}) error: {res['error']['message']}")
                        continue

                    count_yt = 0
                    for item in res.get('items', []):
                        if count_yt >= max_results: break
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
            actor, inp = get_apify_actor_config(plat_name, kw, max_results, days_back)
            if not actor:
                print(f"  No Apify actor configured for {plat_name} yet.")
                continue

            success = False
            estimated_apify_cost = max_results * APIFY_RATE_PER_RESULT.get(plat_name, 0.004)
            if plat_budget_remaining < estimated_apify_cost:
                print(f"  Skipping Apify for {plat_name} because platform budget ({plat_budget_remaining}$) is below estimated cost ({estimated_apify_cost}$)")
                continue
            if overall_remaining < estimated_apify_cost:
                print(f"  Skipping Apify for {plat_name} because overall budget ({overall_remaining}$) is below estimated cost ({estimated_apify_cost}$)")
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
                        if count_apify >= max_results: break
                        if not item or 'error' in item: continue

                        normalized = normalize_apify_item(item, plat_name, cutoff_utc)
                        if normalized and normalized.get('url'):
                            normalized['date'] = format_to_bkk(normalized.get('date'))
                            if plat_name == 'LinkedIn' and normalized.get('is_old'):
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
                print(f"  All Apify Tokens exhausted or not configured for {plat_name}!")
            else:
                plat_budget_remaining -= estimated_apify_cost
                overall_remaining -= estimated_apify_cost
                print(f"  Deducted {estimated_apify_cost}$ for Apify call | Platform budget: {plat_budget_remaining}$ | Overall budget: {overall_remaining}$")
                if plat_budget_remaining < 0:
                    plat_budget_remaining = 0.0
                if overall_remaining < 0:
                    overall_remaining = 0.0

    return all_videos, plat_budget_remaining, overall_remaining

def main():
    global gc

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
            global_cfg, platform_configs = read_platform_configs(ws_control)

            if not is_run_active(global_cfg['status']):
                print(f"\nStop signal detected from Control_Panel. Exiting loop.")
                break

            platforms = list(platform_configs.keys())
            if not platforms:
                print(f"\nNo active platforms configured. Exiting loop.")
                break

            reset_result = check_and_reset_daily_budget(ws_control, global_cfg, platform_configs)
            if reset_result is not None:
                global_cfg, platform_configs = reset_result

            print(f"\n\nProcessing Batch: {get_bkk_now().strftime('%H:%M:%S')} (Platforms: {platforms}, Overall Budget: {global_cfg['overall_remaining']}$)")

            now = get_bkk_now()
            all_raw = []
            scraped_platforms = []
            for plat_name, cfg in platform_configs.items():
                last_exec = cfg.get('last_execution')
                if last_exec is not None:
                    elapsed = (now - last_exec).total_seconds()
                    if elapsed < cfg['interval_min'] * 60:
                        remaining = int(cfg['interval_min'] * 60 - elapsed)
                        print(f"  Skipping {plat_name} — last run {last_exec.strftime('%H:%M:%S')}, next in {remaining}s")
                        continue

                videos, cfg['budget_remaining'], global_cfg['overall_remaining'] = fetch_data(
                    plat_name, cfg['keywords'], cfg['max_results'], cfg['days_back'],
                    cfg['budget_remaining'], global_cfg['overall_remaining']
                )
                all_raw.extend(videos)
                cfg['last_execution'] = now
                scraped_platforms.append(plat_name)
            raw_list = all_raw
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
                ws_control.update_cell(3, 2, str(round(global_cfg['overall_remaining'], 4)))
                for _plat_name, cfg in platform_configs.items():
                    ws_control.update_cell(ROW_REMAINING, cfg['col_num'], str(round(cfg['budget_remaining'], 4)))
                    if _plat_name in scraped_platforms and cfg.get('last_execution'):
                        ws_control.update_cell(ROW_LAST_EXECUTION, cfg['col_num'],
                            cfg['last_execution'].strftime('%Y-%m-%d %H:%M:%S'))
                print(f"Updated budget state")
            except Exception as e:
                print(f"Failed to persist budget: {e}")

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

            print("\nCycle complete. Exiting for Watchdog re-trigger.")
            break

        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
