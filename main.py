from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
import requests
import math
import base64
import time
import asyncio  # ✅ Delay ke liye
import difflib  # ✅ Fuzzy matching ke liye

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNELS = ["@stree2chaava2", "@chaava2025"]
FORWARD_CHANNEL = -1002512169097
ALERT_CHANNEL = -1002661392627

DB_FILE = "movie_db.json"
REPO = "shree95692/movie-db-backup"
BRANCH = "main"
GITHUB_FILE_PATH = "movie_db.json"
GITHUB_PAT = os.environ.get("GITHUB_PAT")

def restore_db_from_github():
    if not GITHUB_PAT:
        print("No GitHub PAT found, skipping restore.")
        return
    try:
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{REPO}/contents/{GITHUB_FILE_PATH}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json().get("content")
            if content:
                decoded = base64.b64decode(content)
                with open(DB_FILE, "wb") as f:
                    f.write(decoded)
                print("✅ movie_db.json restored from GitHub.")
        else:
            print("Failed to fetch from GitHub:", response.text)
    except Exception as e:
        print("Restore failed:", e)

# ✅ Always restore before building DB
restore_db_from_github()

EXTRA_PHRASES = [
    "in hindi", "hindi dubbed", "south movie", "movie", "drama",
    "watch online", "download", "latest", "full movie"
]

def clean_title(title):
    title = title.lower()  # 🔽 Convert to lowercase

    for phrase in EXTRA_PHRASES:
        title = title.replace(phrase, "")  # ❌ Remove phrases like "hindi dubbed", "full movie", etc.

    title = re.sub(r'\d{4}', '', title)      # ❌ Removes things like (2023), (2011)
    title = re.sub(r'\d{4}', '', title)          # ❌ Removes years like 2023, 2024 (even without brackets)
    title = re.sub(r'[^a-z0-9\s]', '', title)    # ❌ Removes symbols like . , - ( ) etc.
    title = re.sub(r'\s+', ' ', title).strip()   # ✅ Cleans extra spaces

    return title

# ✅ Move this BELOW clean_title()
movie_db = {}

try:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        raw_db = json.load(f)
except Exception as e:
    print(f"❌ Failed to load DB: {e}")
    raw_db = {}

if raw_db:
    for title, data in raw_db.items():
        clean_key = clean_title(title)
        entries = []

        if isinstance(data, list):
            if len(data) == 2 and all(isinstance(i, str) for i in data):
                entries.append(tuple(data))
            else:
                for item in data:
                    if isinstance(item, list) and len(item) == 2:
                        entries.append(tuple(item))
        elif isinstance(data, tuple) and len(data) == 2:
            entries.append(data)
        elif isinstance(data, str):
            match = re.search(r"t\.me/(.+)/(\d+)", data)
            if match:
                entries.append(("@" + match.group(1), int(match.group(2))))

        # Remove duplicates
        seen = set()
        unique = []
        for ch, msg_id in entries:
            uid = f"{ch}_{msg_id}"
            if uid not in seen:
                seen.add(uid)
                unique.append((ch, msg_id))

        if unique:
            existing = movie_db.get(clean_key, [])
            if isinstance(existing, tuple):
                existing = [existing]
            elif not isinstance(existing, list):
                existing = []

            all_entries = unique + existing
            seen = set()
            merged = []
            for ch, msg_id in all_entries:
                uid = f"{ch}_{msg_id}"
                if uid not in seen:
                    seen.add(uid)
                    merged.append((ch, msg_id))

            movie_db[clean_key] = merged if len(merged) > 1 else [merged[0]]
else:
    print("⚠️ No movie data loaded into memory.")
    movie_db = {}

print(f"📦 Total movies loaded: {len(movie_db)}")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_db():
    if not movie_db:
        print("⚠️ movie_db is empty. Skipping save to avoid overwriting backup.")
        return

    def format_entry(entry):
        # ✅ Flat entry like ["@channel", msg_id]
        if isinstance(entry, list) and len(entry) == 2 and all(isinstance(i, (str, int)) for i in entry):
            return entry
        # ✅ Multi-posts like [["@channel", msg_id], ["@channel2", msg_id2]]
        elif isinstance(entry, list) and all(isinstance(i, (list, tuple)) and len(i) == 2 for i in entry):
            return [list(i) for i in entry]
        # ✅ Tuple like ("@channel", msg_id)
        elif isinstance(entry, tuple) and len(entry) == 2:
            return list(entry)
        return entry  # Fallback (rare)

    def get_latest_msg_id(entry):
        entries = []
        if isinstance(entry, list):
            entries = [e for e in entry if isinstance(e, (list, tuple)) and len(e) == 2]
        elif isinstance(entry, tuple) and len(entry) == 2:
            entries = [entry]
        msg_ids = [msg_id for _, msg_id in entries if isinstance(msg_id, int)]
        return max(msg_ids, default=0)

    # ✅ Sort by latest message id (descending)
    sorted_db = dict(sorted(movie_db.items(), key=lambda item: get_latest_msg_id(item[1]), reverse=True))
    # ✅ Format entries
    formatted_db = {k: format_entry(v) for k, v in sorted_db.items()}

    with open(DB_FILE, "w", encoding="utf-8") as f:
        # ✅ Compact one-liner per entry
        json.dump(formatted_db, f, ensure_ascii=False, indent=2, separators=(',', ': '))

    # ✅ Push to GitHub
    if GITHUB_PAT:
        try:
            with open(DB_FILE, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            push_to_github(content)
        except Exception as e:
            print("GitHub push failed:", e)

def push_to_github(content):
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{REPO}/contents/{GITHUB_FILE_PATH}"
    get_response = requests.get(url, headers=headers)
    sha = get_response.json().get("sha")

    data = {
        "message": "Update movie_db.json",
        "content": content,
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    print("📤 GitHub push status:", response.status_code)

def extract_title(text):
    match = re.search(r'[🎬🎥🗨️🔰⭐📽️]\s*(?:title\s*:)?\s*(.+)', text, re.IGNORECASE)
    if match:
        return clean_title(match.group(1))
    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel registered successfully!")
        await message.reply_text("Alert channel registered.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to register:\n{e}")

@bot.on_message(filters.command("init_channels"))
async def init_channels(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added
    errors = []

    try:
        await client.send_message(FORWARD_CHANNEL, "✅ Forward channel connected.")
    except Exception as e:
        errors.append(f"❌ Forward error:\n{e}")

    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel connected.")
    except Exception as e:
        errors.append(f"❌ Alert error:\n{e}")

    await message.reply_text("\n\n".join(errors) if errors else "✅ Both channels initialized.")

@bot.on_message(filters.command("list_movies"))
async def list_movies(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added
    page = 1
    try:
        args = message.text.split()
        if len(args) > 1:
            page = int(args[1])
    except:
        pass

    valid_movies = []
    for title, data in movie_db.items():
        entries = []
        if isinstance(data, tuple) and len(data) == 2:
            entries = [data]
        elif isinstance(data, list):
            entries = [e for e in data if isinstance(e, (list, tuple)) and len(e) == 2]
        else:
            continue

        for ch, msg_id in entries:
            try:
                msg = await client.get_messages(ch, msg_id)
                if msg and (msg.text or msg.caption):
                    latest_msg_id = msg.id
                    valid_movies.append((title, latest_msg_id))
                    break
            except:
                continue

    # Sort by msg_id descending (latest first)
    valid_movies.sort(key=lambda x: x[1], reverse=True)

    total_pages = math.ceil(len(valid_movies) / 20)
    if page < 1 or page > total_pages:
        await message.reply_text(f"❌ Page not found. Total pages: {total_pages}")
        return

    start = (page - 1) * 20
    end = start + 20
    page_movies = valid_movies[start:end]

    text = f"📽️ Valid Movies (Page {page}/{total_pages})\n\n"
    for i, (title, _) in enumerate(page_movies, start=start + 1):
        text += f"{i}. {title.title()}\n"

    await message.reply_text(text)

@bot.on_message(filters.command("add_movie"))
async def add_movie_cmd(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added

    if message.from_user.id != 5163916480:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        _, data = message.text.split(" ", 1)
        title, link = data.split("|", 1)
        link = link.strip()
        match = re.search(r"t\.me/(.+)/(\d+)", link)
        if match:
            channel = "@" + match.group(1)
            msg_id = int(match.group(2))

            key = clean_title(title.strip())

            existing = movie_db.get(key, [])
            if isinstance(existing, tuple):
                existing = [existing]
            elif not isinstance(existing, list):
                existing = []

            combined = [(channel, msg_id)] + existing

            # Remove duplicates
            seen = set()
            merged = []
            for ch, msg in combined:
                uid = f"{ch}_{msg}"
                if uid not in seen:
                    seen.add(uid)
                    merged.append((ch, msg))

            movie_db[key] = merged if len(merged) > 1 else [merged[0]]
            save_db()
            await message.reply_text(f"✅ Added manually: {title}")
        else:
            await message.reply_text("❌ Invalid link format. Use /add_movie Movie Name | https://t.me/channel/123")
    except:
        await message.reply_text("❌ Usage: /add_movie Movie Name | https://t.me/channel/123")
@bot.on_message(
    filters.incoming &
    (filters.private | filters.group) &
    filters.text &
    ~filters.command(["start", "register_alert", "init_channels", "list_movies", "add_movie"])
)
async def search_movie(client, message: Message):
    await asyncio.sleep(0.9)

    query = message.text.strip()
    if not query or query.startswith("/"):
        return

    greetings = ["hi", "hello", "hii", "ok", "okay", "hey", "heyy"]
    if query.lower() in greetings:
        await message.reply_text("Hello 👋")
        return

    query_clean = clean_title(query)

    # ✅ Exact match check
    for title, data in movie_db.items():
        if clean_title(title) == query_clean:
            entries = []
            if isinstance(data, tuple):
                entries = [data]
            elif isinstance(data, list):
                entries = [entry for entry in data if isinstance(entry, (list, tuple)) and len(entry) == 2]

            valid_results = []
            valid_entries = []

            for ch, msg_id in entries:
                try:
                    msg = await client.get_messages(ch, msg_id)
                    if msg and (msg.text or msg.caption):
                        valid_results.append(f"https://t.me/{ch.strip('@')}/{msg_id}")
                        valid_entries.append((ch, msg_id))
                except:
                    continue

            if valid_entries:
                movie_db[clean_title(title)] = valid_entries if len(valid_entries) > 1 else [valid_entries[0]]
                save_db()

            if valid_results:
                await message.reply_text("🎬 Movie found:\n" + "\n".join(valid_results))
                return
            else:
                movie_db.pop(clean_title(title), None)
                save_db()

    # ✅ Fuzzy match check
    def similarity(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

    scored_matches = []
    for title, data in movie_db.items():
        title_clean = clean_title(title)
        score = similarity(query_clean, title_clean)
        if score >= 0.4:
            entries = []
            if isinstance(data, tuple):
                entries = [data]
            elif isinstance(data, list):
                entries = [entry for entry in data if isinstance(entry, (list, tuple)) and len(entry) == 2]

            for ch, msg_id in entries:
                scored_matches.append((score, title, ch, msg_id))

    scored_matches.sort(reverse=True)

    valid_results = []
    valid_entries_by_title = {}

    for score, title, ch, msg_id in scored_matches[:5]:
        try:
            msg = await client.get_messages(ch, msg_id)
            if msg and (msg.text or msg.caption):
                valid_results.append((score, f"https://t.me/{ch.strip('@')}/{msg_id}"))
                clean_key = clean_title(title)
                valid_entries_by_title.setdefault(clean_key, []).append((ch, msg_id))
        except:
            continue

    for clean_key, entries in valid_entries_by_title.items():
        movie_db[clean_key] = entries if len(entries) > 1 else [entries[0]]
    if valid_entries_by_title:
        save_db()

    # ✅ Strict fuzzy threshold
    if valid_results and max(score for score, _ in valid_results) >= 0.8:
        await message.reply_text("🎬 Matching movies:\n" + "\n".join(link for _, link in valid_results))
    else:
        await message.reply_text(
            f"❌ Movie nahi mili bhai 😔\n"
            f"South movie bahubalii part 2 ❌ Bahubali 2 ✅\n"
            f"🔍 Ek baar naam ki spelling Google se check kar lo.\n"
            f"📩 Request mil gayi hai!\n"
            f"⏳ 5-6 ghante me upload ho jayegi.\n"
            f"🍿 Tab tak popcorn leke chill maro!"
        )
        if message.from_user:
            await client.send_message(
                ALERT_CHANNEL,
                text=f"❌ Movie not found: {query}\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
            )
@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    await asyncio.sleep(0.9)  # ✅ Delay added
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title and len(title.strip()) >= 2:
            def normalize_title(title):
                title = title.lower()
                title = re.sub(r'\d{4}', '', title)
                title = re.sub(r'\d{4}', '', title)
                title = re.sub(r'\s+', ' ', title).strip()
                return title

            normalized_new = normalize_title(title)
            matching_titles = [t for t in movie_db if normalize_title(t) == normalized_new]

            new_link = f"https://t.me/{chat_username.strip('@')}/{message.id}"

            valid_links = []
            updated_entry = []

            for t in matching_titles:
                data = movie_db.get(t)
                entries = []
                if isinstance(data, tuple):
                    entries = [data]
                elif isinstance(data, list):
                    entries = [entry for entry in data if isinstance(entry, tuple) and len(entry) == 2]

                for ch, msg_id in entries:
                    try:
                        msg = await client.get_messages(ch, msg_id)
                        if msg:
                            valid_links.append(f"https://t.me/{ch.strip('@')}/{msg_id}")
                            updated_entry.append((ch, msg_id))
                    except Exception as e:
                        print(f"⚠️ Fetch failed for {t}: {e}")

            valid_links.append(new_link)
            updated_entry.append((chat_username, message.id))

            if len(valid_links) > 1:
                alert_text = (
                    f"⚠️ Duplicate movie detected: {title.title()}\n\n"
                    f"🔁 All related posts:\n" + "\n".join(valid_links)
                )
                try:
                    await client.send_message(ALERT_CHANNEL, alert_text)
                except Exception as e:
                    print("⚠️ Duplicate alert send failed:", e)

            key = clean_title(title)
            existing = movie_db.get(key, [])
            if isinstance(existing, tuple):
                existing = [existing]
            elif not isinstance(existing, list):
                existing = []

            combined = [(chat_username, message.id)] + existing
            seen = set()
            final = []
            for ch, msg_id in combined:
                uid = f"{ch}_{msg_id}"
                if uid not in seen:
                    seen.add(uid)
                    final.append((ch, msg_id))

            movie_db[key] = final if len(final) > 1 else [final[0]]
            save_db()
            print(f"✅ Saved: {title} -> {chat_username}/{message.id}")

            try:
                await client.send_message(FORWARD_CHANNEL, f"🎬 New Movie Added: {title.title()}")
            except Exception as e:
                await client.send_message(
                    ALERT_CHANNEL,
                    text=f"❗ Message send failed:\n{new_link}\nError: {e}"
                )
        else:
            await client.send_message(
                ALERT_CHANNEL,
                f"⚠️ Title detect nahi hua for post: https://t.me/{message.chat.username}/{message.id}"
            )
    else:
        print("⚠️ Unknown channel.")
def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("✅ movie_db.json restored from GitHub.")
    print("🚀 Starting Flask server...")
    Thread(target=run_flask).start()
    print("🤖 Starting Telegram bot...")
    bot.run()
