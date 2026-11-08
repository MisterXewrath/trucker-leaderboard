import discord
from discord.ext import commands
import sqlite3
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "miles.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            username  TEXT    NOT NULL,
            miles     REAL    NOT NULL,
            timestamp TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn

# ── Bot setup ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ── Helpers ───────────────────────────────────────────────

def ordinal(n):
    """1→1st, 2→2nd, 3→3rd, etc."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th'][min(n%10,4)]}"

def format_leaderboard(rows, title, emoji="🚛"):
    """rows: list of (username, total_miles)"""
    if not rows:
        return f"**{emoji} {title}**\nNo trips logged yet!"

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"**{emoji} {title}**\n"]
    for i, (username, miles) in enumerate(rows):
        rank = medals[i] if i < 3 else f"**{ordinal(i+1)}**"
        lines.append(f"{rank}  **{username}** — {miles:,.1f} miles")
    return "\n".join(lines)

def get_leaderboard(period=None, limit=10):
    """period: 'week', 'month', or None (all-time)"""
    conn = get_db()
    if period == "week":
        cutoff = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime("%Y-%m-%d 00:00:00")
        # Monday of this week
        rows = conn.execute(
            "SELECT username, SUM(miles) as total FROM trips WHERE timestamp >= ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()
    elif period == "month":
        cutoff = datetime.utcnow().strftime("%Y-%m-01 00:00:00")
        rows = conn.execute(
            "SELECT username, SUM(miles) as total FROM trips WHERE timestamp >= ? GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT username, SUM(miles) as total FROM trips GROUP BY user_id ORDER BY total DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return rows

def get_user_stats(user_id):
    conn = get_db()
    now = datetime.utcnow()
    week_cutoff = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
    month_cutoff = now.strftime("%Y-%m-01 00:00:00")

    alltime   = conn.execute("SELECT COALESCE(SUM(miles),0), COUNT(*) FROM trips WHERE user_id=?", (user_id,)).fetchone()
    weekly    = conn.execute("SELECT COALESCE(SUM(miles),0), COUNT(*) FROM trips WHERE user_id=? AND timestamp>=?", (user_id, week_cutoff)).fetchone()
    monthly   = conn.execute("SELECT COALESCE(SUM(miles),0), COUNT(*) FROM trips WHERE user_id=? AND timestamp>=?", (user_id, month_cutoff)).fetchone()
    conn.close()
    return {
        "alltime":  {"miles": alltime[0],  "trips": alltime[1]},
        "weekly":   {"miles": weekly[0],   "trips": weekly[1]},
        "monthly":  {"miles": monthly[0],  "trips": monthly[1]},
    }

# ── Commands ──────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

@bot.command(name="newtrip")
async def newtrip(ctx, miles: str = None):
    """Log a new trip.  Usage: !newtrip 450"""
    if miles is None:
        await ctx.send("⚠️ Usage: `!newtrip <miles>`  — e.g. `!newtrip 450`")
        return

    try:
        miles = float(miles.replace(",", ""))
    except ValueError:
        await ctx.send("⚠️ That doesn't look like a number. Try `!newtrip 450`")
        return

    if miles <= 0:
        await ctx.send("⚠️ Miles must be a positive number.")
        return
    if miles > 10000:
        await ctx.send("⚠️ That's over 10,000 miles in one trip — sure about that? Max is 10,000 per entry.")
        return

    conn = get_db()
    conn.execute(
        "INSERT INTO trips (user_id, username, miles, timestamp) VALUES (?, ?, ?, datetime('now'))",
        (ctx.author.id, ctx.author.display_name, miles)
    )
    conn.commit()
    conn.close()

    stats = get_user_stats(ctx.author.id)
    embed = discord.Embed(
        title="🚛 Trip Logged!",
        description=f"**{ctx.author.display_name}** just drove **{miles:,.1f}** miles!",
        color=0x2ecc71
    )
    embed.add_field(name="This Week",  value=f"{stats['weekly']['miles']:,.1f} mi ({stats['weekly']['trips']} trips)", inline=True)
    embed.add_field(name="This Month", value=f"{stats['monthly']['miles']:,.1f} mi ({stats['monthly']['trips']} trips)", inline=True)
    embed.add_field(name="All-Time",   value=f"{stats['alltime']['miles']:,.1f} mi ({stats['alltime']['trips']} trips)", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx, period: str = None):
    """
    Show leaderboard.
    !leaderboard          → all-time
    !leaderboard week     → this week
    !leaderboard month    → this month
    !lb                   → shortcut
    """
    period_map = {
        "week": ("week", "Weekly Leaderboard (Mon–Sun)"),
        "weekly": ("week", "Weekly Leaderboard (Mon–Sun)"),
        "w": ("week", "Weekly Leaderboard (Mon–Sun)"),
        "month": ("month", "Monthly Leaderboard"),
        "monthly": ("month", "Monthly Leaderboard"),
        "m": ("month", "Monthly Leaderboard"),
    }

    if period and period.lower() in period_map:
        p, title = period_map[period.lower()]
    else:
        p, title = None, "All-Time Leaderboard"

    rows = get_leaderboard(period=p)
    embed = discord.Embed(
        description=format_leaderboard(rows, title),
        color=0x3498db
    )
    await ctx.send(embed=embed)

@bot.command(name="mystats", aliases=["stats", "me"])
async def mystats(ctx):
    """Show your personal stats."""
    stats = get_user_stats(ctx.author.id)
    if stats["alltime"]["trips"] == 0:
        await ctx.send("You haven't logged any trips yet! Use `!newtrip <miles>` to get started.")
        return

    embed = discord.Embed(
        title=f"📊 Stats for {ctx.author.display_name}",
        color=0x9b59b6
    )
    embed.add_field(name="🗓️ This Week",  value=f"**{stats['weekly']['miles']:,.1f}** miles\n{stats['weekly']['trips']} trips", inline=True)
    embed.add_field(name="📅 This Month", value=f"**{stats['monthly']['miles']:,.1f}** miles\n{stats['monthly']['trips']} trips", inline=True)
    embed.add_field(name="🏆 All-Time",   value=f"**{stats['alltime']['miles']:,.1f}** miles\n{stats['alltime']['trips']} trips", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="undo")
async def undo(ctx):
    """Delete your most recent trip entry."""
    conn = get_db()
    row = conn.execute(
        "SELECT id, miles FROM trips WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (ctx.author.id,)
    ).fetchone()
    if not row:
        await ctx.send("You have no trips to undo.")
        conn.close()
        return
    conn.execute("DELETE FROM trips WHERE id=?", (row[0],))
    conn.commit()
    conn.close()
    await ctx.send(f"✅ Removed your last trip ({row[1]:,.1f} miles).")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🚛 Trucker Leaderboard — Commands",
        color=0xe67e22
    )
    embed.add_field(name="!newtrip <miles>", value="Log a trip (e.g. `!newtrip 450`)", inline=False)
    embed.add_field(name="!leaderboard [week|month]", value="Show the leaderboard (alias: `!lb`)", inline=False)
    embed.add_field(name="!mystats", value="See your personal stats (alias: `!me`)", inline=False)
    embed.add_field(name="!undo", value="Delete your last logged trip", inline=False)
    await ctx.send(embed=embed)

# ── Run ───────────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Set DISCORD_TOKEN in .env or environment")
    exit(1)

bot.run(TOKEN)
