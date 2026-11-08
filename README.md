# Trucker Leaderboard Bot 🚛

A Discord bot that tracks miles driven by community members with weekly, monthly, and all-time leaderboards.

## Setup

1. **Create a Discord bot** at https://discord.com/developers/applications
   - New Application → Bot → copy the token
   - Enable **Message Content Intent** under Bot → Privileged Gateway Intents

2. **Paste your token** into `.env`:
   ```
   DISCORD_TOKEN=your-bot-token-here
   ```

3. **Install dependencies & run**:
   ```bash
   pip install discord.py python-dotenv
   python bot.py
   ```

4. **Invite the bot** to your server with this URL (replace `CLIENT_ID`):
   ```
   https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=2048&scope=bot
   ```

## Commands

| Command | Description |
|---|---|
| `!newtrip <miles>` | Log a trip (e.g. `!newtrip 450`) |
| `!leaderboard` | All-time leaderboard (alias: `!lb`) |
| `!leaderboard week` | This week's leaderboard |
| `!leaderboard month` | This month's leaderboard |
| `!mystats` | Your personal stats (alias: `!me`) |
| `!undo` | Remove your last logged trip |
| `!help` | Show all commands |

## Data

All data is stored in `miles.db` (SQLite) in the same folder. Back up this file to preserve all trip history.
