# main.py

import threading
import time
from pathlib import Path

from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram import Update

from config import TELEGRAM_BOT_TOKEN, CHECK_INTERVAL
from panel import login, fetch_all_numbers
from cache import load_cache, save_cache
from compare import compare_states
from file_map import register_file as register


# ================= TXT FILE RECEIVED HANDLER =================
async def handle_txt(update, context):
    if update.message.document and update.message.document.file_name.endswith(".txt"):
        await update.message.reply_text(
            "📄 TXT file detected!\n\n"
            "To add this file for monitoring:\n"
            "<b>Reply</b> to this file & send command:\n\n"
            "<code>/add</code>\n",
            parse_mode="HTML"
        )


# ================= /add COMMAND HANDLER =================
async def cmd_add(update, context):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠ Reply this command to a TXT file.")

    doc = update.message.reply_to_message.document
    if not doc or not doc.file_name.endswith(".txt"):
        return await update.message.reply_text("⚠ Reply must be to a valid .txt file.")

    file = await doc.get_file()
    Path("uploads").mkdir(exist_ok=True)
    file_path = f"uploads/{doc.file_name}"
    await file.download_to_drive(file_path)

    nums = [i.strip() for i in open(file_path) if i.strip().isdigit()]
    register(doc.file_name, nums)

    await update.message.reply_text(
        f"📁 File Added: <b>{doc.file_name}</b>\n"
        f"🔢 Numbers Saved: <b>{len(nums)}</b>\n"
        f"🕒 Monitoring will alert automatically!",
        parse_mode="HTML"
    )


# ================= MONITOR LOOP =================
def monitor_loop():
    print("🚀 Starting Auto Monitor System\n")

    if not login():
        print("❌ Cannot login, exiting monitor loop.")
        return

    current_state = fetch_all_numbers()
    save_cache(current_state)
    print("💾 Initial state saved to panel_cache.json\n")

    while True:
        try:
            print(f"\n⏳ Waiting {CHECK_INTERVAL} seconds before next check...\n")
            time.sleep(CHECK_INTERVAL)

            try:
                new_state = fetch_all_numbers()
            except Exception as e:
                print(f"⚠ Error fetching numbers: {e}")
                print("🔁 Trying to re-login...")
                if login():
                    new_state = fetch_all_numbers()
                else:
                    print("❌ Re-login failed, skipping this cycle.")
                    continue

            old_state = load_cache()
            compare_states(old_state, new_state)
            save_cache(new_state)

        except KeyboardInterrupt:
            print("🛑 Monitor stopped by user.")
            break
        except Exception as e:
            print(f"❌ Unexpected error in monitor loop: {e}")
            time.sleep(30)


# ================= MAIN =================
if __name__ == "__main__":
    # Start monitor loop in background
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

    print("🤖 Telegram listener active... waiting for TXT uploads")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_txt))
    app.add_handler(CommandHandler("add", cmd_add))

    app.run_polling(close_loop=False)
