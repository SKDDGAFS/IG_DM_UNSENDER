# Instagram DM Unsender 🗑️

A Python script to automatically delete all your messages from any Instagram DM conversation.

## ⚠️ Important Warning
This tool uses Instagram's **private API** (not the official one).  
- **Use at your own risk** - Instagram may temporarily rate-limit or flag your account
- The script includes a 1-second delay between deletions to minimize risk
- I am not responsible for any account restrictions that may occur

## What It Does
- ✅ Login securely (session saved for future use)
- ✅ List all your DM conversations
- ✅ Select which conversation to clean
- ✅ Delete ALL messages YOU sent in that conversation
- ✅ Confirmation required before deleting (prevents accidents)

## Requirements
- Python 3.8 or higher
- instagrapi library

## Installation

1. **Clone this repository**
bash
git clone https://github.com/YOUR_USERNAME/instagram-dm-unsender.git
cd instagram-dm-unsender
Install required library

bash
pip install instagrapi
Run the script

bash
python dm_unsender.py
How To Use
Login - Enter your Instagram username and password (session saved for next time)

View conversations - See all your DM chats with participants and last message time

Select conversation - Pick which chat to clean up

Confirm deletion - Type "DELETE" to confirm (this cannot be undone!)

Wait - Script deletes messages one-by-one with delays to avoid rate limits

Features
🔒 Secure password input - Password hidden while typing

💾 Session saving - No need to login every time

🐢 Rate limit protection - 1-second delay between each deletion

⚠️ Confirmation required - Prevents accidental deletion

📊 Progress tracking - See how many messages deleted/skipped

Files
dm_unsender.py - The main script

session.json - Stores your login session (auto-created, ignored by Git)

.gitignore - Prevents sensitive files from being uploaded to GitHub

Safety Tips
Don't delete messages too frequently

Avoid using this tool multiple times in a short period

Consider testing on an old conversation first

Only delete messages you're sure you want gone

Common Issues
Issue	Solution
"instagrapi could not be resolved"	Run pip install instagrapi
Login fails repeatedly	Instagram may be blocking the login, wait 24 hours
"Too many requests" error	You're being rate-limited, wait before trying again
Script crashes mid-deletion	Messages already deleted won't come back, run again for remaining
Disclaimer
This tool is for educational purposes only. It interacts with Instagram's private API which violates their Terms of Service. The developer assumes no liability for any consequences of using this software.

License
This project is open source and free to use. No warranty provided.

Made with Python 🐍
