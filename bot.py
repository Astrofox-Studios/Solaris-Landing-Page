import asyncio
import discord
from discord.ui import View
import threading
import time
import logging

log = logging.getLogger(__name__)

CHANNEL_ID    = 1504788982158856282
REQUIRED_ROLE = 1240650335647957063
TTL           = 120  # seconds a request lives before auto-expiry

# ── Shared state (accessed from both Flask and bot threads) ───────────────────

_pending: dict = {}
_lock    = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None

# ── Discord client ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot     = discord.Client(intents=intents)


class ApprovalView(View):
    def __init__(self, req_id: str):
        super().__init__(timeout=TTL)
        self.req_id = req_id

    async def _resolve(self, interaction: discord.Interaction, approved: bool):
        member = interaction.user
        # In a guild context discord.py v2 gives us a Member with roles populated
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Must be used inside the server.", ephemeral=True)
            return

        if not any(r.id == REQUIRED_ROLE for r in member.roles):
            await interaction.response.send_message(
                "You don't have permission to handle login requests.", ephemeral=True
            )
            return

        with _lock:
            entry = _pending.get(self.req_id)
            if not entry:
                await interaction.response.send_message("Request has expired.", ephemeral=True)
                return
            if entry["status"] != "pending":
                await interaction.response.send_message("Already resolved.", ephemeral=True)
                return
            entry["status"] = "approved" if approved else "denied"
            entry["actor"]  = member.display_name

        for child in self.children:
            child.disabled = True

        embed       = interaction.message.embeds[0]
        embed.color = discord.Color.green() if approved else discord.Color.red()
        action      = "✅ Approved" if approved else "❌ Denied"
        embed.set_footer(text=f"{action} by {member.display_name}")
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        with _lock:
            e = _pending.get(self.req_id)
            if e and e["status"] == "pending":
                e["status"] = "expired"

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, False)


async def _dispatch(req_id: str, ip: str, ua: str):
    # Wait up to 15 s for the bot to finish connecting
    for _ in range(30):
        if bot.is_ready():
            break
        await asyncio.sleep(0.5)
    else:
        log.error("Bot not ready after 15 s — approval message not sent for %s", req_id)
        return

    try:
        ch = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
    except Exception as exc:
        log.error("Cannot reach approval channel: %s", exc)
        return

    embed = discord.Embed(
        title="🔐 Admin Login Request",
        description="Password accepted. Approve or deny this login.",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="IP", value=f"`{ip}`", inline=True)
    embed.add_field(name="Expires", value="2 min", inline=True)
    if ua:
        embed.add_field(
            name="User Agent",
            value=(ua[:117] + "…") if len(ua) > 120 else ua,
            inline=False,
        )
    embed.set_footer(text=f"ID {req_id[:8]}")

    await ch.send(embed=embed, view=ApprovalView(req_id))


@bot.event
async def on_ready():
    log.info("Discord auth bot ready as %s", bot.user)


# ── Public API (called from Flask thread) ─────────────────────────────────────

def create_request(req_id: str, ip: str, ua: str) -> None:
    with _lock:
        _pending[req_id] = {"status": "pending", "expires": time.time() + TTL}
    if _loop:
        asyncio.run_coroutine_threadsafe(_dispatch(req_id, ip, ua), _loop)
    else:
        log.error("Bot loop not running — cannot send approval request")


def get_status(req_id: str) -> str:
    with _lock:
        e = _pending.get(req_id)
        if not e:
            return "expired"
        if e["status"] == "pending" and time.time() > e["expires"]:
            e["status"] = "expired"
        return e["status"]


def consume(req_id: str) -> bool:
    """Removes and returns True only if status is approved."""
    with _lock:
        if _pending.get(req_id, {}).get("status") == "approved":
            del _pending[req_id]
            return True
        return False


def start(token: str) -> None:
    global _loop

    def _run():
        global _loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop = loop
        try:
            loop.run_until_complete(bot.start(token))
        except Exception as exc:
            log.error("Bot runner crashed: %s", exc)

    threading.Thread(target=_run, daemon=True, name="discord-auth-bot").start()
