from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import requests

netznutzungsentgelt = 5.37 # c / kWh
netzverlustentgelt = 0.33
eletrizitätsabgabe = 0.10

async def spot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    marketdata = requests.get('https://api.awattar.at/v1/marketdata').json()['data']
    end_data = []
    new_line = '\n'
    for element in marketdata:
        start_time = datetime.fromtimestamp(int(element['start_timestamp']) / 1000)
        price = element['marketprice']
        end_data.append(f'{start_time.strftime("%d-%m-%Y - %H:%M")} - {price}€')

    await update.message.reply_text(f'Hallo {update.effective_user.first_name}!\n'
                                    f'Hier der Spotpreis pro MWh für Heute:\n\n'
                                    f'{new_line.join(map(str, end_data))}')


async def kWh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    marketdata = requests.get('https://api.awattar.at/v1/marketdata').json()['data']
    end_data = []
    new_line = '\n'

    message_text = update.message.text.split(' ', 1)

    if len(message_text) > 1:
        command, content = message_text
        if content:
            num_kwh = int(content)
    else:
        num_kwh = 1

    for element in marketdata:
        start_time = datetime.fromtimestamp(int(element['start_timestamp']) / 1000)
        price_MWh = element['marketprice']
        price = ((price_MWh / 10) + netznutzungsentgelt + netzverlustentgelt + eletrizitätsabgabe) * 1.2
        end_data.append(f'{start_time.strftime("%d-%m-%Y - %H:%M")} - {round(price * num_kwh, 2)}c')

    await update.message.reply_text(f'Hallo {update.effective_user.first_name}!\n'
                                    f'Hier der Preis pro kWh für Heute:\n\n'
                                    f'{new_line.join(map(str, end_data))}')


async def set_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global netznutzungsentgelt
    global netzverlustentgelt
    global eletrizitätsabgabe

    message_text = update.message.text.split(' ', 3)
    if len(message_text) == 3:
        command, variable, value = message_text
        match variable.lower():
            case "netznutzungsentgelt":
                netznutzungsentgelt = float(value)
            case "netzverlustentgelt":
                netzverlustentgelt = float(value)
            case "eletrizitätsabgabe":
                eletrizitätsabgabe = float(value)
        await update.message.reply_text(f'Value of {variable} has been set to {value}')
    else:
        await update.message.reply_text(f'Not possible')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = "Available commands:\n"
    help_text += "/spot - Get current Spot-Prices from aWATTar\n"
    help_text += "/kWh [num] - Get the price per kWh. If 'num' is set, multiple the values with 'num'.\n"
    help_text += "/set_value [name] [value] - Set [name] to [value].\n"
    help_text += "/help - Display this help message"
    help_text += ("\n\nInfo - Netzkosten Nettopreis:\n"
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
app.add_handler(CommandHandler("kWh", kWh))
app.add_handler(CommandHandler("set_value", set_value))
app.add_handler(CommandHandler("help", help_command))

print("Application started - waiting for messages!")

app.run_polling()
