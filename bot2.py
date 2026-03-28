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


# ================== 봇 시작 ==================
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(PaymentView())
    print(f"✅ S2 Bot online! ({client.user})")

client.run(TOKEN)
