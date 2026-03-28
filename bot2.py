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
                    f"✅ 아래 링크에서 결제를 완료해주세요!\n{data['url']}\n\n결제 완료 후 자동으로 역할이 부여됩니다.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ 결제 링크 생성에 실패했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

        except Exception as e:
            print(f"[S2 Bot] 결제 링크 생성 오류: {e}")
            await interaction.followup.send("❌ 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)


# ================== 셋업 명령어 ==================
@tree.command(name="setup-payment", description="결제 안내 메시지 설정")
async def setup_payment(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
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
    print(f"✅ S2 Bot 온라인! ({client.user})")

client.run(TOKEN)
