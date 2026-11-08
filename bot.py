import discord
from discord.ext import commands
import sqlite3
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────

DAILY_MILE_LIMIT = 1000  # max miles per user in a rolling 24h window
ADMIN_ROLE_NAME = "Trucker Admin"  # users with this role get admin commands

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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ── Helpers ───────────────────────────────────────────────

def is_admin(ctx):
    """Check if user has the admin role or is server owner."""
    if ctx.author.id == ctx.guild.owner_id:
        return True
    return any(r.name == ADMIN_ROLE_NAME for r in ctx.author.roles)

def ordinal(n):
    """1->1st, 2->2nd, 3->3rd, etc."""
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

def get_daily_miles(user_id):
    """Get total miles logged in the last 24 hours."""
    conn = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        "SELECT COALESCE(SUM(miles),0) FROM trips WHERE user_id=? AND timestamp>=?",
        (user_id, cutoff)
    ).fetchone()
    conn.close()
    return row[0]

# ── Easter Eggs ───────────────────────────────────────────

EASTER_EGGS = {
    69: [
        "Nice. 😏",
        "Nice miles, trucker. Real nice. 😏🚛",
        "Giggity. 69 miles logged. 😏",
    ],
    420: [
        "Blaze it! 🔥🚛💨",
        "Rolling down the highway... rolling something else too? 🌿",
        "420 miles?? That's a high mileage trip! 😶‍🌫️",
    ],
    666: [
        "Highway to Hell! 🔥😈🚛",
        "The devil's haul! Satan rides shotgun. 😈",
        "Beelzebub called — he wants his miles back. 👹",
    ],
    1337: [
        "L33T trucker detected! 🎮🚛",
        "h4x0r on the highway! 1337 miles logged. 💻",
        "You just pwned the leaderboard. 🏆",
    ],
    80085: [
        "Classic calculator move. 🧮😂",
        "I see what you did there... 👀",
    ],
    8008: [
        "Calculator comedy, very mature. 🧮😏",
        "Ah yes, the ol' calculator special. 👀",
    ],
    1: [
        "One single mile? Did you move the truck out of the driveway? 🤣",
        "Bro really logged 1 mile. Parking lot king. 👑",
    ],
    2: [
        "Two miles? That's barely past the truck stop. ⛽",
    ],
    13: [
        "Unlucky number! Hope the rig's okay. 🍀🚛",
    ],
    7: [
        "Lucky number 7! 🎰🚛",
    ],
    100: [
        "💯 miles! A perfect hundo!",
    ],
    404: [
        "404: Rest stop not found. 🚫🛑",
        "Error 404: Miles not— wait, they were found. Carry on. 🚛",
    ],
    187: [
        "187 on an undercover trucker! 🚔🚛",
    ],
    500: [
        "500 miles! And you would drive 500 more 🎵🚛",
    ],
    123: [
        "Easy as 1-2-3! 🚛✨",
    ],
    999: [
        "So close to a thousand... but not quite. 😤🚛",
    ],
    777: [
        "JACKPOT! 🎰🎰🎰 Lucky trucker!",
    ],
    911: [
        "Emergency miles! Hope everything's okay out there. 🚨🚛",
    ],
}

def get_easter_egg(miles):
    """Return an easter egg message if miles is a funny number, else None."""
    int_miles = int(miles) if miles == int(miles) else None
    if int_miles and int_miles in EASTER_EGGS:
        return random.choice(EASTER_EGGS[int_miles])
    # Check for repeating digits (111, 222, 333, etc.)
    if int_miles and len(str(int_miles)) >= 3 and len(set(str(int_miles))) == 1:
        return f"{'🚛' * len(str(int_miles))} {str(int_miles)[0]}'s across the board!"
    return None

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

    # ── Daily limit check ──
    daily_so_far = get_daily_miles(ctx.author.id)
    if daily_so_far + miles > DAILY_MILE_LIMIT:
        remaining = max(0, DAILY_MILE_LIMIT - daily_so_far)
        await ctx.send(
            f"⚠️ Daily limit is **{DAILY_MILE_LIMIT:,.0f} miles** per 24 hours.\n"
            f"You've already logged **{daily_so_far:,.1f}** today. "
            f"You can still log **{remaining:,.1f}** more miles."
        )
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

    # ── Easter egg ──
    egg = get_easter_egg(miles)
    if egg:
        embed.set_footer(text=egg)

    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx, period: str = None):
    """
    Show leaderboard.
    !leaderboard          -> all-time
    !leaderboard week     -> this week
    !leaderboard month    -> this month
    !lb                   -> shortcut
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

    daily = get_daily_miles(ctx.author.id)
    remaining = max(0, DAILY_MILE_LIMIT - daily)

    embed = discord.Embed(
        title=f"📊 Stats for {ctx.author.display_name}",
        color=0x9b59b6
    )
    embed.add_field(name="🗓️ This Week",  value=f"**{stats['weekly']['miles']:,.1f}** miles\n{stats['weekly']['trips']} trips", inline=True)
    embed.add_field(name="📅 This Month", value=f"**{stats['monthly']['miles']:,.1f}** miles\n{stats['monthly']['trips']} trips", inline=True)
    embed.add_field(name="🏆 All-Time",   value=f"**{stats['alltime']['miles']:,.1f}** miles\n{stats['alltime']['trips']} trips", inline=True)
    embed.add_field(name="⏱️ Daily Budget", value=f"**{remaining:,.1f}** of {DAILY_MILE_LIMIT:,} mi remaining", inline=False)
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

# ── Admin Commands ────────────────────────────────────────

@bot.command(name="admin-reset")
async def admin_reset(ctx, member: discord.Member = None):
    """Delete ALL trips for a user. Admin only."""
    if not is_admin(ctx):
        await ctx.send("🚫 You need the **Trucker Admin** role to use this.")
        return
    if member is None:
        await ctx.send("⚠️ Usage: `!admin-reset @user`")
        return

    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM trips WHERE user_id=?", (member.id,)).fetchone()[0]
    if count == 0:
        await ctx.send(f"**{member.display_name}** has no trips to delete.")
        conn.close()
        return
    conn.execute("DELETE FROM trips WHERE user_id=?", (member.id,))
    conn.commit()
    conn.close()
    await ctx.send(f"🗑️ Deleted **{count}** trips for **{member.display_name}**.")

@bot.command(name="admin-remove")
async def admin_remove(ctx, member: discord.Member = None, count: int = 1):
    """Remove the last N trips for a user. Admin only.  Usage: !admin-remove @user 3"""
    if not is_admin(ctx):
        await ctx.send("🚫 You need the **Trucker Admin** role to use this.")
        return
    if member is None:
        await ctx.send("⚠️ Usage: `!admin-remove @user [count]`")
        return

    conn = get_db()
    rows = conn.execute(
        "SELECT id, miles FROM trips WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (member.id, count)
    ).fetchall()
    if not rows:
        await ctx.send(f"**{member.display_name}** has no trips to remove.")
        conn.close()
        return
    ids = [r[0] for r in rows]
    total_miles = sum(r[1] for r in rows)
    conn.execute(f"DELETE FROM trips WHERE id IN ({','.join('?' * len(ids))})", ids)
    conn.commit()
    conn.close()
    await ctx.send(f"🗑️ Removed **{len(rows)}** trip(s) ({total_miles:,.1f} miles) from **{member.display_name}**.")

@bot.command(name="admin-addmiles")
async def admin_addmiles(ctx, member: discord.Member = None, miles: str = None):
    """Add miles to a user (bypasses daily limit). Admin only.  Usage: !admin-addmiles @user 500"""
    if not is_admin(ctx):
        await ctx.send("🚫 You need the **Trucker Admin** role to use this.")
        return
    if member is None or miles is None:
        await ctx.send("⚠️ Usage: `!admin-addmiles @user <miles>`")
        return

    try:
        miles = float(miles.replace(",", ""))
    except ValueError:
        await ctx.send("⚠️ That doesn't look like a number.")
        return

    conn = get_db()
    conn.execute(
        "INSERT INTO trips (user_id, username, miles, timestamp) VALUES (?, ?, ?, datetime('now'))",
        (member.id, member.display_name, miles)
    )
    conn.commit()
    conn.close()
    await ctx.send(f"✅ Added **{miles:,.1f} miles** to **{member.display_name}** (admin override).")

@bot.command(name="admin-stats")
async def admin_stats(ctx):
    """Show server-wide stats. Admin only."""
    if not is_admin(ctx):
        await ctx.send("🚫 You need the **Trucker Admin** role to use this.")
        return

    conn = get_db()
    total_miles = conn.execute("SELECT COALESCE(SUM(miles),0) FROM trips").fetchone()[0]
    total_trips = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM trips").fetchone()[0]

    now = datetime.utcnow()
    day_cutoff = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    week_cutoff = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
    month_cutoff = now.strftime("%Y-%m-01 00:00:00")

    day_miles = conn.execute("SELECT COALESCE(SUM(miles),0) FROM trips WHERE timestamp>=?", (day_cutoff,)).fetchone()[0]
    week_miles = conn.execute("SELECT COALESCE(SUM(miles),0) FROM trips WHERE timestamp>=?", (week_cutoff,)).fetchone()[0]
    month_miles = conn.execute("SELECT COALESCE(SUM(miles),0) FROM trips WHERE timestamp>=?", (month_cutoff,)).fetchone()[0]

    top = conn.execute("SELECT username, SUM(miles) as total FROM trips GROUP BY user_id ORDER BY total DESC LIMIT 1").fetchone()
    conn.close()

    embed = discord.Embed(title="📈 Server Stats", color=0xe74c3c)
    embed.add_field(name="Total Drivers", value=f"**{total_users}**", inline=True)
    embed.add_field(name="Total Trips", value=f"**{total_trips:,}**", inline=True)
    embed.add_field(name="Total Miles", value=f"**{total_miles:,.1f}**", inline=True)
    embed.add_field(name="Last 24h", value=f"{day_miles:,.1f} mi", inline=True)
    embed.add_field(name="This Week", value=f"{week_miles:,.1f} mi", inline=True)
    embed.add_field(name="This Month", value=f"{month_miles:,.1f} mi", inline=True)
    if top:
        embed.add_field(name="🏆 Top Driver", value=f"**{top[0]}** — {top[1]:,.1f} mi", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="admin-setlimit")
async def admin_setlimit(ctx, new_limit: str = None):
    """Change the daily mile limit. Admin only.  Usage: !admin-setlimit 1500"""
    global DAILY_MILE_LIMIT
    if not is_admin(ctx):
        await ctx.send("🚫 You need the **Trucker Admin** role to use this.")
        return
    if new_limit is None:
        await ctx.send(f"Current daily limit: **{DAILY_MILE_LIMIT:,} miles**\nUsage: `!admin-setlimit <miles>`")
        return
    try:
        new_limit = float(new_limit.replace(",", ""))
    except ValueError:
        await ctx.send("⚠️ That doesn't look like a number.")
        return
    if new_limit < 1:
        await ctx.send("⚠️ Limit must be at least 1 mile.")
        return
    DAILY_MILE_LIMIT = new_limit
    await ctx.send(f"✅ Daily limit updated to **{DAILY_MILE_LIMIT:,.0f} miles**.")

# ── Help ──────────────────────────────────────────────────

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

    if is_admin(ctx):
        embed.add_field(name="\u200b", value="**🔧 Admin Commands**", inline=False)
        embed.add_field(name="!admin-reset @user", value="Delete all trips for a user", inline=False)
        embed.add_field(name="!admin-remove @user [N]", value="Remove last N trips for a user", inline=False)
        embed.add_field(name="!admin-addmiles @user <miles>", value="Add miles (bypasses daily limit)", inline=False)
        embed.add_field(name="!admin-stats", value="Server-wide stats overview", inline=False)
        embed.add_field(name="!admin-setlimit <miles>", value="Change daily mile limit", inline=False)

    await ctx.send(embed=embed)

# ── Run ───────────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Set DISCORD_TOKEN in .env or environment")
    exit(1)

bot.run(TOKEN)
