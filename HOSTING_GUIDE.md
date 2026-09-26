# How to Publish Your Discord Bot (24/7 Hosting)

Right now, your bot is running on your computer. If you turn off your computer or close the terminal, the bot goes offline. To make it run 24/7, you need to "host" it on a server in the cloud. 

Here are the most popular ways to host a Python Discord bot:

---

## Option 1: Discord Bot Hosts (Easiest & Cheapest)
There are hosting companies specifically designed for Discord bots and game servers. They provide a simple panel where you just upload your files and click "Start".
- **PebbleHost** (~$3/month): Extremely reliable and very easy to use.
- **Sparked Host** (~$1/month): Very cheap and perfectly fine for a small bot.

**How to do it:**
1. Buy a basic Python Bot hosting plan.
2. They will give you access to a web panel (usually Pterodactyl).
3. Zip your bot files (`bot.py`, `cogs/`, `requirements.txt`, `.env`, and `hotlines.json`) and upload them to the panel.
4. Go to the panel's "Startup" tab and make sure the startup command is `python bot.py`.
5. Click Start!

---

## Option 2: Cloud Services like Render or Railway (Modern & Automated)
These services link directly to your GitHub account. When you update your code on GitHub, they automatically restart your bot with the new code!
- **Render.com**: Has a free tier (though free tiers usually sleep if inactive, which is bad for music bots. A paid "Background Worker" is ~$7/month).
- **Railway.app**: Very popular, costs around $5/month depending on usage.

**How to do it:**
1. Upload your code to a **Private** GitHub repository. *(CRITICAL: DO NOT upload your `.env` file to GitHub, or hackers will steal your bot token!)*
2. Create an account on Render or Railway and link your GitHub.
3. Create a new "Background Worker" (Render) or "Service" (Railway).
4. Set the Build Command to `pip install -r requirements.txt`.
5. Set the Start Command to `python bot.py`.
6. Add your `DISCORD_TOKEN` as an "Environment Variable" in their dashboard settings (since you didn't upload your `.env` file).

---

## Option 3: VPS / Virtual Private Server (Most Control)
This is literally just renting a small Linux computer in the cloud. It requires a bit of Linux terminal knowledge but is the professional standard.
- **DigitalOcean** (~$6/month)
- **Linode / Akamai** (~$5/month)
- **AWS EC2** (Has a 1-year free tier for micro instances)

**How to do it:**
1. Rent an Ubuntu server.
2. Connect to it via SSH.
3. Install Python and FFmpeg (`sudo apt install python3-pip ffmpeg`).
4. Upload your files using SFTP (like FileZilla) or `git clone`.
5. Run your bot using a process manager like `pm2` or `tmux` so it stays running when you close the terminal.

---

## ⚠️ Important Checklist Before Publishing

Before you upload your bot anywhere, make sure you do the following:
1. **Never share your Token**: Keep your `.env` file safe. If your token ever leaks online, Discord will automatically reset it, and you'll have to generate a new one in the Developer Portal.
2. **Install FFmpeg**: Your bot plays music using FFmpeg. If you use a VPS, you MUST install FFmpeg on that server (`sudo apt install ffmpeg`). If you use a Bot Host (Option 1), they usually have it pre-installed.
3. **hotlines.json**: If you have saved hotlines, make sure to upload your `hotlines.json` file to the server so it remembers them!
