import logging
import sqlite3
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# ដាក់ Token របស់អ្នកនៅទីនេះ
BOT_TOKEN = '8186524970:AAElShrY0gvM7GAPTBctgR4CJ3mELFgUAzs'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- ផ្នែក Database ---
def init_db():
    conn = sqlite3.connect('aba_finance.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            currency TEXT,
            date TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_transaction(amount, currency, date_obj):
    conn = sqlite3.connect('aba_finance.db')
    c = conn.cursor()
    c.execute("INSERT INTO transactions (amount, currency, date) VALUES (?, ?, ?)", 
              (amount, currency, date_obj))
    conn.commit()
    conn.close()

def get_report(period):
    conn = sqlite3.connect('aba_finance.db')
    c = conn.cursor()
    
    query = ""
    if period == 'day':
        query = "SELECT currency, SUM(amount) FROM transactions WHERE date(date) = date('now') GROUP BY currency"
    elif period == 'month':
        query = "SELECT currency, SUM(amount) FROM transactions WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') GROUP BY currency"
    elif period == 'year':
        query = "SELECT currency, SUM(amount) FROM transactions WHERE strftime('%Y', date) = strftime('%Y', 'now') GROUP BY currency"
        
    c.execute(query)
    results = c.fetchall()
    conn.close()
    return results

# --- ផ្នែកដំណើរការសារ (Core Logic) ---

async def handle_aba_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    pattern = r"([៛$])([\d,]+(?:\.\d+)?) paid by"
    match = re.search(pattern, text)

    if match:
        symbol = match.group(1)
        amount_str = match.group(2)
        
        currency = "KHR" if symbol == "៛" else "USD"
        amount = float(amount_str.replace(",", ""))
        trx_date = update.message.date
        
        save_transaction(amount, currency, trx_date)
        
        await update.message.reply_text(
            f"✅ បានកត់ត្រា៖ {amount:,.2f} {currency}\n"
            f"📅 កាលបរិច្ឆេទ៖ {trx_date.strftime('%Y-%m-%d')}"
        )

# --- ផ្នែកបញ្ជាមើលរបាយការណ៍ ---

async def report_handler(update: Update, period: str):
    data = get_report(period)
    
    if not data:
        await update.message.reply_text(f"📭 មិនមានទិន្នន័យសម្រាប់ {period} នេះទេ។")
        return

    msg = f"📊 **របាយការណ៍ {period}**\n"
    msg += "------------------\n"
    
    for row in data:
        curr, total = row
        symbol = "៛" if curr == "KHR" else "$"
        msg += f"{curr}: {symbol}{total:,.2f}\n"
        
    await update.message.reply_text(msg, parse_mode='Markdown')

async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await report_handler(update, 'day')

async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await report_handler(update, 'month')

async def yearly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await report_handler(update, 'year')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! សូម Forward សារពី ABA PayWay ចូលមកទីនេះ។\n"
        "បញ្ជាមើលរបាយការណ៍៖ /day, /month, /year"
    )

# --- Main Program ---
if __name__ == '__main__':
    init_db()
    
    # ចំណុចសំខាន់ដែលបានកែ៖ បន្ថែម .job_queue(None) ដើម្បីបិទមុខងារកំណត់ម៉ោង
    app = ApplicationBuilder().token(BOT_TOKEN).job_queue(None).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('day', daily_report))
    app.add_handler(CommandHandler('month', monthly_report))
    app.add_handler(CommandHandler('year', yearly_report))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_aba_message))
    
    print("ABA Bot is running...")
    app.run_polling()