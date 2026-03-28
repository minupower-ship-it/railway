import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()

TOKEN      = os.getenv('DISCORD_TOKEN')
RENDER_URL = "https://xh-7vlt.onrender.com"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree   = app_commands.CommandTree(client)

# ================== 채널 ID ==================
CHANNELS = {
    "xxx": 1487520341151449091,
}

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
                await interaction.followup.send(
                    "❌ Failed to generate payment link. Please try again later.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"[S2 Bot] Payment link error: {e}")
            await interaction.followup.send(
                "❌ Server error. Please try again later.",
                ephemeral=True
            )


# ================== 셋업 명령어 ==================
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
    embed.add_field(
        name="Price",
        value="**One-time payment** — Lifetime access",
        inline=False
    )
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
        view = ChannelSelectView(
            post_name=self.post_name.value,
            file_size=self.file_size.value,
            key=self.key.value,
            link=self.link.value,
            image_url=self.image_url.value
        )
        await interaction.response.send_message(
            "📢 Select a channel to post in:",
            view=view,
            ephemeral=True
        )


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

        view = RevealLinkView(link=self.link)

        if isinstance(channel, discord.ForumChannel):
            await channel.create_thread(
                name=f"{self.post_name} — {self.file_size}",
                embed=embed,
                view=view
            )
        else:
            await channel.send(embed=embed, view=view)

        await interaction.response.send_message("✅ Posted successfully!", ephemeral=True)


class RevealLinkView(discord.ui.View):
    def __init__(self, link: str):
        super().__init__(timeout=None)
        self.link = link

    @discord.ui.button(label="Reveal Link", style=discord.ButtonStyle.primary, emoji="🔓", custom_id="s2_reveal_link")
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🔗 **Your VIP link:**\n{self.link}",
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


# ================== 봇 시작 ==================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PaymentView())
    client.add_view(PostButtonView())
    print(f"✅ S2 Bot online! ({client.user})")

client.run(TOKEN)
