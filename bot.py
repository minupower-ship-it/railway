import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import aiohttp
import json
import io
import openpyxl

load_dotenv()

TOKEN             = os.getenv('DISCORD_TOKEN')
RENDER_URL        = "https://xh-7vlt.onrender.com"
API_SECRET_KEY    = os.getenv('API_SECRET_KEY')
LINK_STORE_ID      = 1488022953525248141  # XHouse Dummy 채널 ID
PREVIEW_CHANNEL_ID = 1487501681129422980  # preview 채널
EDMONTON_TZ        = ZoneInfo("America/Edmonton")
SUPPORT_CHANNEL_ID = int(os.getenv('SUPPORT_CHANNEL_ID', '0'))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)

# ================== 채널 ID ==================
CHANNELS = {
    "🇭🇮🇸🇵🇦🇳🇮🇨":       1487319298681864342,
    "🇼🇭🇮🇹🇪":            1487319326204625047,
    "🇧🇱🇦🇨🇰":            1487319363265626173,
    "🇦🇸🇮🇦🇳-🇴🇹🇭🇪🇷🇸": 1487319260228358174,
    "🇨🇴🇱🇱🇦🇧s":         1489310534544265376,
}

# ================== TXT 채널 매핑 ==================
CHANNEL_MAP = {
    "asian":    1487319260228358174,  # 🇦🇸🇮🇦🇳-🇴🇹🇭🇪🇷🇸
    "hispanic": 1487319298681864342,  # 🇭🇮🇸🇵🇦🇳🇮🇨
    "white":    1487319326204625047,  # 🇧‌🇱‌🇦‌🇨‌🇰‌
    "black":    1487319363265626173,  # 🇧🇱🇦🇨🇰
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
    async for message in channel.history(limit=None):
        if message.content.startswith(f"{thread_id} |"):
            parts = message.content.split(" | ", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None

# ================== Content Request ==================
class ContentRequestModal(discord.ui.Modal, title="Content Request Form"):
    name    = discord.ui.TextInput(label="Name", placeholder="Your name", required=True, max_length=100)
    link    = discord.ui.TextInput(label="Link (OF / X 등)", placeholder="https://...", required=True)
    comment = discord.ui.TextInput(label="Comment", placeholder="Additional comments", required=False, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            request_channel = await client.fetch_channel(1486473063649247352)
        except Exception:
            request_channel = None
        if request_channel:
            embed = discord.Embed(title="🆕 New Content Request", description="A new content request has been submitted!", color=0x9b59b6, timestamp=datetime.utcnow())
            embed.add_field(name="Requested By", value=f"{interaction.user.display_name}\n({interaction.user.name})", inline=True)
            embed.add_field(name="Name", value=self.name.value, inline=True)
            embed.add_field(name="Content Link", value=self.link.value, inline=False)
            if self.comment.value and self.comment.value.strip():
                embed.add_field(name="Comment", value=self.comment.value, inline=False)
            embed.set_footer(text=f"Requested at • {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
            await request_channel.send(embed=embed)
            await interaction.response.send_message("✅ Your request has been submitted successfully!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Request channel not found. Please contact an admin.", ephemeral=True)


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
    embed = discord.Embed(title="Welcome to #request-form!", description="Submit your content requests here.", color=0x2b2d31)
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
                    headers={"Content-Type": "application/json", "X-API-Key": API_SECRET_KEY}
                ) as res:
                    data = await res.json()
            if data.get("url"):
                await interaction.followup.send(
                    f"✅ Complete your payment using the link below!\n{data['url']}\n\nYour role will be granted automatically after payment.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(f"❌ Failed to generate payment link.\nServer response: `{data}`", ephemeral=True)
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
    embed.add_field(name="Lifetime — $45", value="• Private request\n• 1,000+ model packages\n• Lifetime access to all channels\n• Priority support", inline=True)
    embed.add_field(name="VIP Lifetime — $80", value="• Everything in Lifetime\n• Unlimited requests for life\n• Early access to new drops\n• Private personal request", inline=True)
    embed.set_footer(text="One-time payment. No subscriptions. No renewals.")
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
        view = ChannelSelectView(
            post_name=self.post_name.value,
            file_size=self.file_size.value,
            key=self.key.value,
            link=self.link.value,
            image_url=self.image_url.value
        )
        await interaction.response.send_message("📢 Select a channel to post in:", view=view, ephemeral=True)


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
        super().__init__(placeholder="Select channel...", options=options)

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        channel    = client.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
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

        await interaction.response.send_message("✅ Posted successfully!", ephemeral=True)


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



# ================== Auto Post ==================
@tree.command(name="auto-post", description="엑셀 파일로 자동 포스팅 (A:채널 B:이름 C:Mega링크 D+:이미지URL)")
async def auto_post(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # 엑셀 파일 읽기
    try:
        file_bytes = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
        ws = wb.active
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to read Excel file: {e}", ephemeral=True)
        return

    # 행 파싱 (A:채널 B:이름 C:Mega링크 D+:이미지URL)
    parsed = []
    parse_errors = []

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):  # 1행은 헤더
        if not any(row):
            continue

        channel_key = str(row[0]).strip().lower() if row[0] else ""
        folder_name = str(row[1]).strip() if row[1] else ""
        mega_link   = str(row[2]).strip() if row[2] else ""
        image_urls  = [str(c).strip() for c in row[3:] if c and str(c).strip()]

        if not channel_key or not folder_name or not mega_link:
            parse_errors.append(f"Row {i}: A/B/C 컬럼 필수 — 채널/이름/Mega링크")
            continue

        if channel_key not in CHANNEL_MAP:
            parse_errors.append(f"Row {i}: 알 수 없는 채널 `{channel_key}`")
            continue

        if not image_urls:
            parse_errors.append(f"Row {i}: `{folder_name}` — 이미지 URL 없음 (D열 이상 필요)")
            continue

        # Mega 링크에서 키 추출
        key = mega_link.split('#')[-1] if '#' in mega_link else ""

        parsed.append({
            "channel_key": channel_key,
            "folder_name": folder_name,
            "mega_link":   mega_link,
            "key":         key,
            "image_urls":  image_urls,
        })

    if not parsed:
        msg = "❌ No valid rows found.\n"
        if parse_errors:
            msg += "\n".join(parse_errors)
        await interaction.followup.send(msg, ephemeral=True)
        return

    # 중복 방지: Dummy 채널에 이미 저장된 폴더 이름 목록 조회
    existing_names = set()
    store_channel = client.get_channel(LINK_STORE_ID)
    if store_channel:
        async for message in store_channel.history(limit=None):
            content = message.content or ""
            if content.startswith("POSTED | "):
                existing_names.add(content.split("POSTED | ", 1)[1].strip())

    success_list = []
    fail_list    = []
    skip_list    = []

    for item in parsed:
        folder_name = item["folder_name"]
        channel_key = item["channel_key"]
        mega_link   = item["mega_link"]
        key         = item["key"]
        image_urls  = item["image_urls"]
        channel_id  = CHANNEL_MAP[channel_key]
        channel     = client.get_channel(channel_id)

        if not channel:
            fail_list.append(f"❌ `{folder_name}` — Channel not found")
            continue

        # 중복 체크
        if folder_name in existing_names:
            skip_list.append(f"⏭️ `{folder_name}` — Already exists")
            continue

        try:
            embed = discord.Embed(color=0x2b2d31)
            embed.set_image(url=image_urls[0])
            embed.add_field(
                name=folder_name,
                value=f"——————————————————\n🔒 *VIP link hidden*\n\n**Decryption Key:** `{key}`\n——————————————————",
                inline=False
            )

            view = RevealLinkView()

            if isinstance(channel, discord.ForumChannel):
                thread, _ = await channel.create_thread(
                    name=folder_name,
                    embed=embed,
                    view=view
                )
                await save_link(thread.id, mega_link)
                if store_channel:
                    await store_channel.send(f"POSTED | {folder_name}")
                for extra_url in image_urls[1:]:
                    await thread.send(extra_url)
            else:
                msg = await channel.send(embed=embed, view=view)
                await save_link(msg.id, mega_link)
                if store_channel:
                    await store_channel.send(f"POSTED | {folder_name}")
                for extra_url in image_urls[1:]:
                    await channel.send(extra_url)

            success_list.append(f"✅ `{folder_name}` → {channel_key}")

        except Exception as e:
            fail_list.append(f"❌ `{folder_name}` — {str(e)}")

    # 리포트
    report = f"📊 **Auto-Post Report**\n\n"

    if success_list:
        report += f"✅ **Success ({len(success_list)}):**\n"
        report += "\n".join(success_list) + "\n\n"

    if skip_list:
        report += f"⏭️ **Skipped — Already exists ({len(skip_list)}):**\n"
        report += "\n".join(skip_list) + "\n\n"

    if fail_list:
        report += f"❌ **Failed ({len(fail_list)}):**\n"
        report += "\n".join(fail_list) + "\n\n"

    if parse_errors:
        report += f"⚠️ **Parse Errors ({len(parse_errors)}):**\n"
        report += "\n".join(parse_errors)

    # Discord 2000자 제한 → 청크로 나눠서 전송
    chunks = []
    while len(report) > 1900:
        split_at = report.rfind('\n', 0, 1900)
        if split_at == -1:
            split_at = 1900
        chunks.append(report[:split_at])
        report = report[split_at:].lstrip('\n')
    chunks.append(report)

    for i, chunk in enumerate(chunks):
        await interaction.followup.send(chunk, ephemeral=True)

@tree.command(name="setup-post", description="관리자용 포스팅 버튼 설정")
async def setup_post(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return
    embed = discord.Embed(title="📤 Content Post Panel", description="Click the button below to post new content.", color=0x2b2d31)
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


# ================== Support & Review System ==================
class StarSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="⭐  1 Star",           value="1"),
            discord.SelectOption(label="⭐⭐  2 Stars",         value="2"),
            discord.SelectOption(label="⭐⭐⭐  3 Stars",       value="3"),
            discord.SelectOption(label="⭐⭐⭐⭐  4 Stars",     value="4"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐  5 Stars",   value="5"),
        ]
        super().__init__(placeholder="Select your rating...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReviewModal(stars=int(self.values[0])))


class StarRatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(StarSelect())


class ReviewModal(discord.ui.Modal, title="Leave a Review"):
    review_text = discord.ui.TextInput(
        label="Your Review",
        placeholder="Share your experience...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    def __init__(self, stars: int):
        super().__init__()
        self.stars = stars

    async def on_submit(self, interaction: discord.Interaction):
        channel = client.get_channel(SUPPORT_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Error submitting review. Please contact an admin.", ephemeral=True)
            return

        stars_display = "⭐" * self.stars
        embed = discord.Embed(color=0x9b59b6, timestamp=datetime.utcnow())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.description = f'*"{self.review_text.value}"*\n\n{stars_display}'
        embed.set_footer(text=f"{interaction.user.display_name} — Verified Member")

        await channel.send(f"<@{interaction.user.id}> left a review:", embed=embed)
        await interaction.response.send_message("✅ Thank you for your review! We really appreciate it.", ephemeral=True)


class SupportModal(discord.ui.Modal, title="Submit a Support Ticket"):
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Brief description of your issue",
        max_length=100
    )
    message = discord.ui.TextInput(
        label="Message",
        placeholder="Describe your issue in detail...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = client.get_channel(SUPPORT_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Error submitting ticket. Please contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title="🎫 New Support Ticket", color=0x5865f2, timestamp=datetime.utcnow())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Subject", value=self.subject.value, inline=False)
        embed.add_field(name="Message", value=self.message.value, inline=False)
        embed.set_footer(text=f"{interaction.user} • {interaction.user.id}")

        await channel.send(f"<@{interaction.user.id}> submitted a support ticket:", embed=embed)
        await interaction.response.send_message("✅ Your ticket has been submitted! We'll get back to you as soon as possible.", ephemeral=True)


class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="support_ticket")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SupportModal())

    @discord.ui.button(label="Review", style=discord.ButtonStyle.secondary, emoji="⭐", custom_id="review_panel")
    async def review(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "**Select your star rating:**",
            view=StarRatingView(),
            ephemeral=True
        )


@tree.command(name="setup-support", description="Support & Review 패널 설정")
async def setup_support(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return

    embed = discord.Embed(
        title="💬 Support & Reviews",
        description="Need help or want to share your experience? Use the buttons below.",
        color=0x7b6eff
    )
    embed.add_field(name="🎫 Support", value="Having an issue? Submit a ticket and we'll help you out.", inline=False)
    embed.add_field(name="⭐ Review", value="Enjoying the content? Leave us a review — it means a lot!", inline=False)
    view = SupportPanelView()
    await interaction.response.send_message(embed=embed, view=view)


# ================== 자동 Preview 포스팅 ==================
@tasks.loop(time=[
    time(0,  0, tzinfo=EDMONTON_TZ),   # 오전 12시 (자정)
    time(12, 0, tzinfo=EDMONTON_TZ),   # 오후 12시 (정오)
])
async def post_preview():
    channel = client.get_channel(PREVIEW_CHANNEL_ID)
    if not channel:
        return

    # 이전 메시지 삭제
    store = client.get_channel(LINK_STORE_ID)
    if store:
        async for msg in store.history(limit=200):
            if msg.content.startswith("PREVIEW_MSG |"):
                old_id = int(msg.content.split(" | ")[1].strip())
                try:
                    old_msg = await channel.fetch_message(old_id)
                    await old_msg.delete()
                except Exception:
                    pass
                await msg.delete()
                break

    # 새 메시지 포스팅
    new_msg = await channel.send("@everyone\nCheck this free preview!  https://www.xhouse.vip/")

    # 메시지 ID 저장
    if store:
        await store.send(f"PREVIEW_MSG | {new_msg.id}")


# ================== 봇 시작 ==================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(RequestButtonView())
    client.add_view(PostButtonView())
    client.add_view(PaymentView())
    client.add_view(RevealLinkView())
    client.add_view(SupportPanelView())
    post_preview.start()
    print(f"✅ XHouse Bot 온라인! ({client.user})")

client.run(TOKEN)
