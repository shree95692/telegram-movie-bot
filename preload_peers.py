import asyncio
from pyrogram import Client

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "session"  # Agar session file ka naam kuch aur hai toh yaha badlo

# Yeh wo channels hain jinko preload karna hai
CHANNELS = [
    -1002661392627,  # ALERT_CHANNEL_ID
    -1002512169097,  # FORWARD_CHANNEL_ID
    "stree2chaava2", # Channel username bhi chalega
    "chaava2025"
]

async def preload():
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as app:
        print("✅ Logged in.")
        for channel in CHANNELS:
            try:
                chat = await app.get_chat(channel)
                print(f"✅ Loaded: {chat.title} ({chat.id})")
            except Exception as e:
                print(f"❌ Failed: {channel} -> {e}")

asyncio.run(preload())
