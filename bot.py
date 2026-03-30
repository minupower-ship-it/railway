import discord
from discord import app_commands
from datetime import datetime
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()

TOKEN           = os.getenv('DISCORD_TOKEN')
RENDER_URL      = "https://xh-7vlt.onrender.com"
LINK_STORE_ID   = 1488022953525248141  # XHouse Dummy 채널 ID

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)

# ================== 채널 ID ==================
CHANNELS = {
    "🇦🇸🇮🇦🇳":     1487319260228358174,
    "🇭🇮🇸🇵🇦🇳🇮🇨": 1487319298681864342,
    "🇧‌🇱‌🇦‌🇨‌🇰‌":  1487319326204625047,
    "🇧🇱🇦🇨🇰":     1487319363265626173,
}

# ================== 링크 저장/조회 헬퍼 ==================
async def save_link(thread_id: int, link: str):
    channel = client.get_channel(LINK_STORE_ID)
    if channel:
        await channel.send(f"{thread_id} | {link}")

async def get_link(thread_id: int) -> str:
    channel = client.get_channel(LINK_STORE_ID)
    if not channel:
        return None
    async for message in channel.history(limit=500):
        if message.content.startswith(f"{thread_id} |"):
            parts = message.content.split(" | ", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None

# ================== Content Request ==================
class ContentRequestModal(discord.ui.Modal, title="Content Request Form"):
    name    = discord.ui.TextInput(label="Name", placeholder="요청자 이름", required=True, max_length=100)
    link    = discord.ui.TextInput(label="Link (OF / X 등)", placeholder="https://...", required=True)
    comment = discord.ui.TextInput(label="Comment", placeholder="추가 설명", required=False, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        request_channel = discord.utils.get(interaction.guild.text_channels, name="🇷🇪🇶🇺🇪🇸🇹")
        if request_channel:
            embed = discord.Embed(title="🆕 New Content Request", description="A new content request has been submitted!", color=0x9b59b6, timestamp=datetime.now())
            embed.add_field(name="Requested By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Name", value=self.name.value, inline=True)
            embed.add_field(name="Content Link", value=self.link.value, inline=False)
            if self.comment.value and self.comment.value.strip():
                embed.add_field(name="Comment", value=self.comment.value, inline=False)
            embed.set_footer(text=f"Requested at • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            await request_channel.send(embed=embed)
            await interaction.response.send_message("✅ 요청이 성공적으로 접수되었습니다!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ request 채널을 찾을 수 없습니다.", ephemeral=True)


class RequestButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit Content Request", style=discord.ButtonStyle.primary, emoji="📩", custom_id="submit_request")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ContentRequestModal())


@tree.command(name="setup-request", description="request-form 채널에 버튼 설정")
async def setup_request(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return
    embed = discord.Embed(title="#request-form에 오신 걸 환영합니다!", description="#request-form 채널의 시작이에요.", color=0x2b2d31)
    embed.add_field(name="Request Any Model You Want", value="Want access to exclusive content?\n\nGet premium access at **xhouse.vip** and unlock:\n• Unlimited model requests\n• Exclusive content library\n• Priority updates", inline=False)
    view = RequestButtonView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== Payment System ==================
class PaymentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Lifetime — $45", style=discord.ButtonStyle.success, emoji="💳", custom_id="xhouse_lifetime")
    async def get_lifetime(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_payment(interaction, 'lifetime')

    @discord.ui.button(label="Get VIP — $80", style=discord.ButtonStyle.primary, emoji="✨", custom_id="xhouse_vip")
    async def get_vip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_payment(interaction, 'vip')

    async def _handle_payment(self, interaction: discord.Interaction, plan: str):
        await interaction.response.defer(ephemeral=True)
        discord_id = str(interaction.user.id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{RENDER_URL}/create-checkout",
                    json={"plan": plan, "discord_id": discord_id},
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
            print(f"[XHouse Bot] Payment error: {e}")
            await interaction.followup.send("❌ Server error. Please try again later.", ephemeral=True)


@tree.command(name="setup-payment", description="결제 버튼 설정")
async def setup_payment(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return
    embed = discord.Embed(
        title="💎 X-House Membership",
        description="Get lifetime access to exclusive content, model packages, and private channels.",
        color=0x7b6eff
    )
    embed.add_field(name="Lifetime — $45", value="• Private request bot\n• 50,000+ model packages\n• Lifetime access to all channels\n• Priority support", inline=True)
    embed.add_field(name="VIP Lifetime — $80", value="• Everything in Lifetime\n• Unlimited requests for life\n• 3 months early access\n• Private personal request bot", inline=True)
    embed.set_footer(text="One-time payment. No subscriptions. No renewals.")
    view = PaymentView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== Post System ==================
class PostModal(discord.ui.Modal, title="New Content Post"):
    post_name = discord.ui.TextInput(label="Name", placeholder="예: Poppi Louiz", required=True, max_length=100)
    file_size = discord.ui.TextInput(label="File Size", placeholder="예: 10GB", required=True, max_length=20)
    key       = discord.ui.TextInput(label="Decryption Key", placeholder="복호화 키 입력", required=True, max_length=200)
    link      = discord.ui.TextInput(label="VIP Link", placeholder="https://mega.nz/...", required=True)
    image_url = discord.ui.TextInput(label="Image URL", placeholder="https://... (이미지 URL)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        view = ChannelSelectView(
            post_name=self.post_name.value,
            file_size=self.file_size.value,
            key=self.key.value,
            link=self.link.value,
            image_url=self.image_url.value
        )
        await interaction.response.send_message("📢 포스팅할 채널을 선택해주세요:", view=view, ephemeral=True)


class ChannelSelectView(discord.ui.View):
    def __init__(self, post_name, file_size, key, link, image_url):
        super().__init__(timeout=180)
        self.add_item(ChannelSelect(post_name, file_size, key, link, image_url))


class ChannelSelect(discord.ui.Select):
    def __init__(self, post_name, file_size, key, link, image_url):
        self.post_name = post_name
        self.file_size = file_size
        self.key       = key
        self.link      = link
        self.image_url = image_url
        options = [discord.SelectOption(label=name, value=str(ch_id)) for name, ch_id in CHANNELS.items()]
        super().__init__(placeholder="채널 선택...", options=options)

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        channel    = client.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("❌ 채널을 찾을 수 없습니다.", ephemeral=True)
            return

        embed = discord.Embed(color=0x2b2d31)
        embed.set_image(url=self.image_url)
        embed.add_field(
            name=f"{self.post_name} — {self.file_size}",
            value=f"——————————————————\n🔒 *VIP link hidden*\n\n**Decryption Key:** `{self.key}`\n——————————————————",
            inline=False
        )

        view = RevealLinkView()

        if isinstance(channel, discord.ForumChannel):
            thread, _ = await channel.create_thread(
                name=f"{self.post_name} — {self.file_size}",
                embed=embed,
                view=view
            )
            await save_link(thread.id, self.link)
        else:
            msg = await channel.send(embed=embed, view=view)
            await save_link(msg.id, self.link)

        await interaction.response.send_message("✅ 포스팅 완료!", ephemeral=True)


class RevealLinkView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reveal Link", style=discord.ButtonStyle.primary, emoji="🔓", custom_id="reveal_link")
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_id = interaction.channel_id
        link = await get_link(thread_id)
        if link:
            await interaction.response.send_message(f"🔗 **Your VIP link:**\n{link}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Link not found. Please contact an admin.", ephemeral=True)


class PostButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="New Post", style=discord.ButtonStyle.success, emoji="📤", custom_id="new_post")
    async def new_post(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
            return
        await interaction.response.send_modal(PostModal())


@tree.command(name="setup-post", description="관리자용 포스팅 버튼 설정")
async def setup_post(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return
    embed = discord.Embed(title="📤 Content Post Panel", description="새 콘텐츠를 포스팅하려면 아래 버튼을 클릭하세요.", color=0x2b2d31)
    view = PostButtonView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== 기존 포스트 링크 등록 ==================
@tree.command(name="set-link", description="기존 포스트에 링크 등록 (관리자 전용)")
async def set_link(interaction: discord.Interaction, thread_id: str, link: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
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
    client.add_view(RequestButtonView())
    client.add_view(PostButtonView())
    client.add_view(PaymentView())
    client.add_view(RevealLinkView())
    print(f"✅ XHouse Bot 온라인! ({client.user})")

client.run(TOKEN)
