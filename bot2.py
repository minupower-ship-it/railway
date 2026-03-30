import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()

TOKEN           = os.getenv('DISCORD_TOKEN')
RENDER_URL      = "https://xh-7vlt.onrender.com"
LINK_STORE_ID   = 1488005721378521118  # Dummy 채널 ID

# ================== 채널 ID ==================
POST_CHANNEL_ID = 1487520341151449091

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)

# ================== 링크 저장/조회 헬퍼 ==================
async def save_link(thread_id: int, link: str):
    """Dummy 채널에 thread_id | link 저장"""
    channel = client.get_channel(LINK_STORE_ID)
    if channel:
        await channel.send(f"{thread_id} | {link}")

async def get_link(thread_id: int) -> str:
    """Dummy 채널에서 thread_id로 링크 조회"""
    channel = client.get_channel(LINK_STORE_ID)
    if not channel:
        return None
    async for message in channel.history(limit=500):
        if message.content.startswith(f"{thread_id} |"):
            parts = message.content.split(" | ", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None

# ================== 결제 버튼 ==================
class PaymentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Access", style=discord.ButtonStyle.success, emoji="💳", custom_id="s2_get_access")
    async def get_access(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        discord_id = str(interaction.user.id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{RENDER_URL}/s2/create-checkout",
                    json={"discord_id": discord_id},
                    headers={"Content-Type": "application/json"}
                ) as res:
                    data = await res.json()

            if data.get("url"):
                await interaction.followup.send(
                    f"✅ Complete your payment using the link below!\n{data['url']}\n\nYour role will be granted automatically after payment.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ Failed to generate payment link. Please try again later.", ephemeral=True)

        except Exception as e:
            print(f"[S2 Bot] Payment link error: {e}")
            await interaction.followup.send("❌ Server error. Please try again later.", ephemeral=True)


@tree.command(name="setup-payment", description="Set up payment message")
async def setup_payment(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    embed = discord.Embed(
        title="💎 Premium Membership",
        description="Unlock exclusive content and premium features by becoming a member!",
        color=0x7b6eff
    )
    embed.add_field(
        name="What you get:",
        value="• Access to all premium channels\n• Exclusive content library\n• Priority support\n• Lifetime access",
        inline=False
    )
    embed.add_field(name="Price", value="**One-time payment** — Lifetime access", inline=False)
    embed.set_footer(text="Click the button below to get started!")

    view = PaymentView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== Post System ==================
class PostModal(discord.ui.Modal, title="New Content Post"):
    post_name = discord.ui.TextInput(label="Name", placeholder="e.g. Poppi Louiz", required=True, max_length=100)
    file_size = discord.ui.TextInput(label="File Size", placeholder="e.g. 10GB", required=True, max_length=20)
    key       = discord.ui.TextInput(label="Decryption Key", placeholder="Enter decryption key", required=True, max_length=200)
    link      = discord.ui.TextInput(label="VIP Link", placeholder="https://mega.nz/...", required=True)
    image_url = discord.ui.TextInput(label="Image URL", placeholder="https://... (image URL)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        channel = client.get_channel(POST_CHANNEL_ID)

        if not channel:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
            return

        embed = discord.Embed(color=0x2b2d31)
        embed.set_image(url=self.image_url.value)
        embed.add_field(
            name=f"{self.post_name.value} — {self.file_size.value}",
            value=f"——————————————————\n🔒 *VIP link hidden*\n\n**Decryption Key:** `{self.key.value}`\n——————————————————",
            inline=False
        )

        view = RevealLinkView()

        if isinstance(channel, discord.ForumChannel):
            thread, _ = await channel.create_thread(
                name=f"{self.post_name.value} — {self.file_size.value}",
                embed=embed,
                view=view
            )
            # Dummy 채널에 링크 저장
            await save_link(thread.id, self.link.value)
        else:
            msg = await channel.send(embed=embed, view=view)
            await save_link(msg.id, self.link.value)

        await interaction.response.send_message("✅ Posted successfully!", ephemeral=True)


class RevealLinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reveal Link", style=discord.ButtonStyle.primary, emoji="🔓", custom_id="s2_reveal_link")
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 현재 채널(스레드) ID로 링크 조회
        thread_id = interaction.channel_id
        link = await get_link(thread_id)

        if link:
            await interaction.response.send_message(
                f"🔗 **Your VIP link:**\n{link}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Link not found. Please contact an admin.",
                ephemeral=True
            )


class PostButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="New Post", style=discord.ButtonStyle.success, emoji="📤", custom_id="s2_new_post")
    async def new_post(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        await interaction.response.send_modal(PostModal())


@tree.command(name="setup-post", description="Set up admin posting panel")
async def setup_post(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📤 Content Post Panel",
        description="Click the button below to post new content.",
        color=0x2b2d31
    )
    view = PostButtonView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== 기존 포스트 링크 등록 ==================
@tree.command(name="set-link", description="기존 포스트에 링크 등록 (관리자 전용)")
async def set_link(interaction: discord.Interaction, thread_id: str, link: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    channel = client.get_channel(LINK_STORE_ID)
    if channel:
        await channel.send(f"{thread_id} | {link}")
        await interaction.response.send_message(f"✅ Link saved for thread `{thread_id}`!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Storage channel not found.", ephemeral=True)


# ================== 봇 시작 ==================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PaymentView())
    client.add_view(PostButtonView())
    client.add_view(RevealLinkView())
    print(f"✅ S2 Bot online! ({client.user})")

client.run(TOKEN)
