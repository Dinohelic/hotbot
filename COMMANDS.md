# Bot Commands Reference

Here is a complete list of all the commands you can use with your Discord Bot.

**Note:** All commands must start with the `!` prefix.

## Music Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `!join` | Makes the bot join the Voice Channel you are currently in. | `!join` |
| `!play <query>` | Searches for a song, plays a URL, or dials a hotline. If a song is already playing, it will be added to the queue. | `!play lofi hip hop`<br>`!play https://youtube.com/...`<br>`!play 069` |
| `!pause` | Pauses the currently playing song. The song will resume from the same position when you use `!resume`. | `!pause` |
| `!resume` | Resumes a paused song from where it was paused. | `!resume` |
| `!skip` | Skips the currently playing song and starts the next one in the queue. | `!skip` |
| `!stop` | Clears the entire queue, cancels any active loop, stops the music, and disconnects the bot from the Voice Channel. | `!stop` |
| `!queue` | Displays the currently playing song (with a 🔁 loop indicator if active) and up to the next 10 songs in the queue. | `!queue` |

## Loop Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `!loop` | Loops the **currently playing** track infinitely. | `!loop` |
| `!loop <count>` | Loops the **currently playing** track a specific number of times. | `!loop 5` |
| `!loop <song>` | Searches for a song and loops it infinitely. | `!loop starboy` |
| `!loop <count> <song>` | Searches for a song and loops it a specific number of times. | `!loop 3 starboy` |
| `!unloop` | Cancels the active loop. The current play finishes, then the queue continues normally. | `!unloop` |

> **Infinite Loop Vibe Check:** When a track is looping infinitely, the bot will send a check-in message after **30 minutes** asking you to react with 💿 or 🎧. If you don't respond within **5 minutes**, the bot will automatically stop and disconnect to save resources. React to keep the vibes going for another 30!

## Hotline Features

| Command | Description | Example |
| :--- | :--- | :--- |
| `!create_hotline <number> <songs>` | Creates a saved playlist under a specific hotline number. Songs should be separated by commas. You can also paste a YouTube playlist link here! | `!create_hotline 069 never gonna give you up, sandstorm`<br>`!create_hotline 100 <youtube_playlist_url>` |

## Automatic Features (No Command Needed)
- **VC Announcer**: Whenever a user joins a voice channel, the bot will automatically send a message (e.g. `🔊 Anish joined General Voice`) into your configured announcement text channel.
