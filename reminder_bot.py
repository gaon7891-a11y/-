"""
디스코드 리마인더 봇
- '/연장완료' 슬래시 커맨드 입력 시, 24시간 후 해당 채널에 '지금 연장 가능합니다' 메시지 전송
- 봇이 재시작되어도 예약된 리마인더가 유지되도록 JSON 파일에 저장
"""

import discord
from discord import app_commands
from discord.ext import tasks
import json
import os
import datetime

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "여기에_봇_토큰_입력")
DATA_FILE = "reminders.json"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ---------- 저장/불러오기 ----------
def load_reminders():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reminders(reminders):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


# ---------- 슬래시 커맨드 ----------
@tree.command(name="연장완료", description="24시간 후 연장 가능 알림을 받습니다.")
async def extend_command(interaction: discord.Interaction):
   # 1. DB(JSON 파일) 저장용 표준 UTC 시간 계산
    now_utc = datetime.datetime.utcnow()
    remind_at_utc = now_utc + datetime.timedelta(seconds=10)

    reminders = load_reminders()
    reminders.append(
        {
            "channel_id": interaction.channel_id,
            "user_id": interaction.user.id,
            "remind_at": remind_at_utc.isoformat(),  # 저장 및 백그라운드 체크는 원래대로 UTC 기준 처리
        }
    )
    save_reminders(reminders)

    # 2. 안내 메시지 출력용 한국 시간(KST = UTC + 9시간) 계산
    remind_at_kst = remind_at_utc + datetime.timedelta(hours=9)

    # 3. 유저에게는 직관적인 한국 시간(KST)으로 포맷팅하여 안내
    await interaction.response.send_message(
        f"✅ 연장 완료! {remind_at_kst.strftime('%Y-%m-%d %H:%M')} (KST)에 알려드릴게요.",
    
    )


# ---------- 주기적으로 체크하는 백그라운드 태스크 ----------
@tasks.loop(seconds=60)  # 1분마다 체크 (원하면 간격 조절 가능)
async def check_reminders():
    reminders = load_reminders()
    if not reminders:
        return

    now = datetime.datetime.utcnow()
    remaining = []

    for r in reminders:
        remind_at = datetime.datetime.fromisoformat(r["remind_at"])
        if now >= remind_at:
            channel = client.get_channel(r["channel_id"])
            if channel:
                mention = "@everyone"
                try:
                    await channel.send(f"{mention} 지금 연장 가능합니다! https://hub.weirdhost.xyz/server/e8f8ef4c/ **/연장완료** 커맨드 잊지 마세요!")
                except discord.Forbidden:
                    pass  # 채널 접근 권한 없음 등
        else:
            remaining.append(r)  # 아직 시간이 안 된 리마인더는 유지

    save_reminders(remaining)


@check_reminders.before_loop
async def before_check_reminders():
    await client.wait_until_ready()


# ---------- 봇 준비 ----------
@client.event
async def on_ready():
    await tree.sync()  # 슬래시 커맨드 동기화
    check_reminders.start()
    print(f"{client.user} 로그인 완료")


client.run(TOKEN)
