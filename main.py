from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import datetime
import os
import pytz
import requests

netznutzungsentgelt = 5.37  # c / kWh
beschaffungskomponente = 1.5
netzverlustentgelt = 0.33
eletrizitätsabgabe = 0.10


async def spot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    marketdata = requests.get('https://api.awattar.at/v1/marketdata').json()['data']
    end_data = []
    new_line = '\n'
    for element in marketdata:
        start_time = datetime.datetime.fromtimestamp(int(element['start_timestamp']) / 1000)
        price = element['marketprice']
        end_data.append(f'{start_time.strftime("%d-%m-%Y - %H:%M")} - {price}€')

    await update.message.reply_text(f'Hallo {update.effective_user.first_name}!\n'
                                    f'Hier der Spotpreis pro MWh für Heute:\n\n'
                                    f'{new_line.join(map(str, end_data))}')


def get_price(num_kwh: int = 1) -> str:
    marketdata = requests.get('https://api.awattar.at/v1/marketdata').json()['data']
    end_data = []
    for element in marketdata:
        start_time = datetime.datetime.fromtimestamp(int(element['start_timestamp']) / 1000)
        price_mwh = element['marketprice']
        # price with calculation in c/kWh
        price_total = (((price_mwh * 1.03 / 10) +
                        beschaffungskomponente + netznutzungsentgelt + netzverlustentgelt + eletrizitätsabgabe)
                       * 1.2 * num_kwh)
        if price_total > 100:
            price = f"{round(price_total / 100, 2)}€"
        else:
            price = f"{round(price_total, 2)}c"

        end_data.append(f'{start_time.strftime("%d-%m-%Y - %H:%M")} - {price}')

    return '\n'.join(map(str, end_data))


async def kwh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text.split(' ', 1)

    if len(message_text) > 1:
        command, content = message_text
        num_kwh = int(content)
    else:
        num_kwh = 1
    await update.message.reply_text(f'Hallo {update.effective_user.first_name}!\n'
                                    f'Hier der Preis für {num_kwh} kWh Heute:\n{get_price(num_kwh)}')


async def set_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global beschaffungskomponente
    global netznutzungsentgelt
    global netzverlustentgelt
    global eletrizitätsabgabe

    message_text = update.message.text.split(' ', 3)
    if len(message_text) == 3:
        command, variable, value = message_text
        match variable.lower():
            case "netznutzungsentgelt":
                netznutzungsentgelt = float(value)
            case "beschaffungskomponente":
                beschaffungskomponente = float(value)
            case "netzverlustentgelt":
                netzverlustentgelt = float(value)
            case "eletrizitätsabgabe":
                eletrizitätsabgabe = float(value)
        await update.message.reply_text(f'Value of {variable} has been set to {value}')
    else:
        await update.message.reply_text(f'Not possible')


async def daily_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job
    await context.bot.send_message(job.chat_id,
                                   text=f'Hallo hier der Preis für die nächsten 24 Stunden!\n'
                                   f'Hier der kWh Preis für Heute:\n{get_price(1)}')


def remove_job_if_exists(chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(chat_id)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def stop_daily_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Timer successfully cancelled!" if job_removed else "You have no active timer."
    await update.message.reply_text(text)


async def get_daily_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    text = "Timer started. The bot will send a message every day at 14:05!"
    if remove_job_if_exists(str(chat_id), context):
        text += "\nAnd the previous job was removed!"
    tz = pytz.timezone('Europe/Vienna')
    context.job_queue\
        .run_daily(daily_message, time=datetime.time(14, 5, tzinfo=tz), chat_id=chat_id, name=str(chat_id))
    await update.effective_message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = "Available commands:\n"
    help_text += "/spot - Get current Spot-Prices from aWATTar\n"
    help_text += "/kWh [num] - Get the price per kWh. If 'num' is set, multiple the values with 'num'.\n"
    help_text += "/daily - Get the price per kWh daily at 14:05.\n"
    help_text += "/stop - Stop getting the daily price.\n"
    help_text += "/set_value [name] [value] - Set [name] to [value].\n"
    help_text += "/help - Display this help message"
    help_text += ("\n\nInfo - Netzkosten Nettopreis:\n"
                  f"Beschaffungskomponente: {beschaffungskomponente}c/kWh\n"
                  f"Netznutzungsentgelt: {netznutzungsentgelt}c/kWh\n"
                  f"Netzverlustentgelt: {netzverlustentgelt}c/kWh\n"
                  f"Elektrizitätsabgabe: {eletrizitätsabgabe}c/kWh\n")
    await update.message.reply_text(help_text)


bot_token = os.getenv('TOKEN')
if not bot_token:
    print("Environment variable 'TOKEN' is not set - exit!")
    exit(1)

app = ApplicationBuilder().token(bot_token).build()

app.add_handler(CommandHandler("spot", spot))
app.add_handler(CommandHandler("kWh", kwh))
app.add_handler(CommandHandler("set_value", set_value))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("daily", get_daily_messages))
app.add_handler(CommandHandler("stop", stop_daily_messages))

print("Application started - waiting for messages!")

app.run_polling()
