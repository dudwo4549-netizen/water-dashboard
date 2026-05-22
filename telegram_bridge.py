import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# --- [설정] ---
TELEGRAM_TOKEN = "8934663662:AAE7nveJN05lZhy6qOQjhByUs9IckGSvnp0"
GEMINI_API_KEY = "AIzaSyCP27F2xTVHJ35HdnfPX17mL_lyLi9dXnU"
# 💡 무료 티어(Free Tier)에서 실제로 할당량이 존재하는 'gemini-flash-latest'로 변경
GEMINI_MODEL   = "gemini-flash-latest"

# Gemini AI 클라이언트
client = genai.Client(api_key=GEMINI_API_KEY)

# 페르소나 설정
PERSONAS = {
    "seoyong": "당신은 멘탈 케어와 프로젝트 전체 설계를 담당하는 '서용'입니다. 팀장님에게 따뜻하고 긍정적인 에너지를 주며, 거시적인 관점에서 조언하세요. 답변 끝에 항상 팀장님을 응원하는 말을 덧붙이세요.",
    "cheongryong": "당신은 풀스택 개발 및 GIS 코딩 전문가 '청룡'입니다. 기술적인 전문성을 뽐내며, 아주 자신감 있고 명쾌하게 답변하세요. 최신 기술 용어를 적절히 섞어 사용하세요.",
    "dongryong": "당신은 상수도 기술진단 및 정책 전문가 '동룡 기술사'입니다. 한국의 상수도 설계 기준 및 관련 법규에 정통합니다. 매우 신뢰감 있고 엄격하며 전문적인 톤으로 답변하세요.",
    "okryong": "당신은 데이터 분석 및 기술 교육 전문가 '옥룡'입니다. 복잡한 데이터를 쉽게 설명하고, 교육 커리큘럼을 짜는 데 능숙합니다. 친절하고 논리적으로 조목조목 설명하세요."
}

current_persona = "seoyong"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def send_long_message(message_obj, text):
    if not text: return
    for i in range(0, len(text), 4000):
        await message_obj.reply_text(text[i:i+4000])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_keyboard = [['서용', '청룡', '동룡', '옥룡'], ['/status', '/help']]
    await update.message.reply_text(
        f"🙋‍♂️ 안녕 하세요, 팀장님! 실전용 Flash 엔진으로 교체되었습니다.\n"
        f"현재 에이전트: {current_persona}\n"
        "이제 할당량 걱정 없이 말씀해 보세요!",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True),
    )

async def change_persona_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_persona
    text = update.message.text
    mapping = {"서용": "seoyong", "청룡": "cheongryong", "동룡": "dongryong", "옥룡": "okryong"}
    
    if text in mapping:
        current_persona = mapping[text]
        await update.message.reply_text(f"✅ {text} 에이전트가 현장에 투입되었습니다. 말씀을 시작해 주십시오!")
    else:
        try:
            prompt = f"{PERSONAS[current_persona]}\n\n팀장님의 질문: {text}\n\n답변:"
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            await send_long_message(update.message, response.text)
        except Exception as e:
            await update.message.reply_text(f"⚠️ AI 답변 생성 중 오류가 발생했습니다: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task_path = "c:/Users/채송이/Desktop/Antigravity(AI Work)/.mcp_bridge/task.md"
    if os.path.exists(task_path):
        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read()
            await send_long_message(update.message, f"📊 [현재 프로젝트 현황 보고]\n\n{content}")
    else:
        await update.message.reply_text("📂 진행 중인 태스크 파일이 없습니다.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, change_persona_text))

    print(f"[Telegram Bridge] Finalizing with {GEMINI_MODEL}...")
    application.run_polling()

if __name__ == '__main__':
    main()
