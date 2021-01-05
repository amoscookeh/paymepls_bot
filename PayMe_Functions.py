from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, InlineQueryHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from uuid import uuid4
import logging
import pickle
import os

PORT = int(os.environ.get('PORT', 5000))
TOKEN = os.environ['TOKEN']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger(__name__)

# First time starting the bot
def start (update, context):
    format_user_data(update, context)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Welcome to Pay Me Bot &#128176;"
                             + "\n My purpose is to aid you in the collection of money from groups!",
                             parse_mode='HTML')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Before we begin, let me get to know you!\n\nWhat is your name?")
    return USERNAME

# Format user_data for first time start
def format_user_data (update, context):
    context.user_data.clear()
    context.user_data["Polls"] = {}
    context.user_data["Poll Count"] = 0
    context.user_data["Name"] = ""
    context.user_data["Payment methods"] = {}
    context.user_data["User ID"] = update.effective_chat.id

# Update username of user
def update_username (update, context):
    name = update.message.text
    name = " ".join(w.capitalize() for w in name.split())
    context.user_data["Name"] = name
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text= "Nice to meet you " + name + "! \nNow, how would you like others to pay you? (Eg. Bank Transfer, PayNow, PayPal, etc.)")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text= "or press /ready if that's all!")
    return PAYMENT_METHOD

# Update list of payment methods
def update_payment_method (update, context):
    method = update.message.text
    context.user_data["Payment methods"][method] = ""
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Nice, now provide me some information that's linked to {}! (Eg. Link, Acc. Number, etc.)".format(method))
    return LINK

# Update list of payment method information
def update_payment_links (update, context):
    info = update.message.text
    context.user_data["Payment methods"][list(context.user_data["Payment methods"])[-1]] = info
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Alright, now provide me with another payment method (Eg. Bank Transfer, PayNow, PayLah!, etc.) \n\nor press /ready if that's all!")
    return PAYMENT_METHOD

# When user is done with registration
def ready (update, context):
    data = context.user_data
    mesg = "Name: " + data["Name"] + "\n<b>Payment Method</b> : Information"
    for method in data["Payment methods"]:
        mesg += "\n<b>" + method + " : </b>" + data["Payment methods"][method]
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Thank you for providing me with this information! The information you have provided me with is as follows:\n\n" + mesg,
                             parse_mode='html')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="If this information is correct, proceed by using /new to create a new payment! \nOr, use /start to restart registration")
    return registration_handler.END

def cancel_reg (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Data erased. Use /start to restart bot!")
    del context.user_data
    return registration_handler.END

# Create a new payment poll
def new_payment (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome back!" +
                                                                    "\nEnter your title of payment:")

    return TITLE

# Update title of payment poll
def update_title (update, context):
    title = update.message.text
    poll_id = "{}-{}".format(context.user_data["User ID"],context.user_data["Poll Count"])
    context.user_data["Polls"][poll_id] = {"Unpaid":{}, "Paid":{}, "Title":title}
    context.user_data["Poll Count"]+=1
    context.bot.send_message(chat_id=update.effective_chat.id, text="New Payment: " + title)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Nice! Now who owes you money?")

    return NAME

# Add name to payment poll
def update_name (update, context):
    name = update.message.text
    name = " ".join(w.capitalize() for w in name.split())
    polls = context.user_data["Polls"]
    context.user_data["Polls"][list(polls)[-1]]["Unpaid"][name] = 0
    context.bot.send_message(chat_id=update.effective_chat.id, text="How much does this person owe you?")

    return AMOUNT

# Ass amount of money previous added name owes
def update_amount (update, context):
    amount = update.message.text
    try:
        amount = float(amount)
    except:
        update.message.reply_text(
            "Sorry, that was an invalid amount, please try again!"
        )
        return AMOUNT
    polls = context.user_data["Polls"]
    names = context.user_data["Polls"][list(polls)[-1]]["Unpaid"]
    context.user_data["Polls"][list(polls)[-1]]["Unpaid"][list(names)[-1]] = amount

    update.message.reply_text(
        "Well done! Continuing adding names or press /done if you're done!"
    )

    return NAME

# When user is done with poll
def done (update, context):
    poll_id = list(context.user_data["Polls"])[-1]
    poll = generate_poll(context.user_data, poll_id)

    inline_keyboard = [
        [
            InlineKeyboardButton("Publish Payment", switch_inline_query=""),
            InlineKeyboardButton("Delete Payment", callback_data="/dltpoll")
            # InlineKeyboardButton("Turn On Summary", callback_data="/turnOnSummary " + poll_id)
        ]
    ]

    # Data management
    data = context.user_data
    pickle_out = open("{}.pickle".format(poll_id), "wb")
    pickle.dump(data, pickle_out)
    pickle_out.close()

    update.message.reply_html(
        text=poll,
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )

    return ConversationHandler.END

def cancel (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Payment erased. Use /new to create a new payment poll!")
    del context.user_data["Poll"][list(context.user_data["Poll"])[-1]]
    return conv_handler.END

# Poll text generator
def generate_poll (user_data, poll_id):
    title = user_data["Polls"][poll_id]["Title"]
    unpaid = user_data["Polls"][poll_id]["Unpaid"]
    paid = user_data["Polls"][poll_id]["Paid"]
    methods = user_data["Payment methods"]

    poll = "<b>Pay " + user_data["Name"] + " for " + title + "</b>\n"

    if len(unpaid)==0:
        poll += "\n<b>All Payments have been made! Thank you!</b>"
        return poll

    poll += "\n<b>UNPAID:\n</b>"

    for name in unpaid:
        poll += "\n<b>" + str(name) + ":</b> $" + str(unpaid[name])

    poll += "\n\n<b>PAID:</b>\n"

    for name in paid:
        poll += "\n<b>" + str(name) + ":</b> $" + str(paid[name])

    if len(methods)>0:
        poll += "\n\n<b>Pay Me! via:</b>"
        for method in methods:
            poll += "\n<b>" + str(method) + "</b> @ " + str(methods[method])

    return poll

def callbackhandle(update, context):
    query = update.callback_query
    data = query['data'].split()
    command = data[0]
    if command == "/dltpoll":
        query.answer("Payment Deleted")
        dltpoll(update, context)
    elif command == "/paid":
        query.answer("Payment confirmed")
        paid(update, context, data[1], data[2])

# Delete poll from user data
def dltpoll (update, context):
    del context.user_data["Polls"][list(context.user_data["Polls"])[-1]]
    context.user_data["Poll Count"]-=1
    context.bot.send_message(chat_id=update.effective_chat.id, text="Payment deleted!")

# Options to post existing polls
def inlinequery(update, context):
    results = generate_inline_queries(context)
    update.inline_query.answer(results)

# Generate a list of inline queries
def generate_inline_queries(context):
    poll_ids = list(context.user_data["Polls"])  # Empty dictionaries in Python return false when bool(dict)

    inline_queries = []
    for poll_id in poll_ids:
        inline_keyboards = []
        title = context.user_data["Polls"][poll_id]["Title"]
        for name in context.user_data["Polls"][poll_id]["Unpaid"]:
            inline_keyboards.append(InlineKeyboardButton(name, callback_data="/paid " + name + " " + poll_id))
        query = InlineQueryResultArticle(id=uuid4(), title=title,
                                         input_message_content=InputTextMessageContent(generate_poll(context.user_data, poll_id), parse_mode='HTML'),
                                         reply_markup=InlineKeyboardMarkup([inline_keyboards])
                                         )
        inline_queries.append(query)

    return inline_queries

def paid(update, context, name, poll_id):
    query = update.callback_query
    # Edit information in the user data
    pickle_in = open("{}.pickle".format(poll_id), "rb")
    data = pickle.load(pickle_in)
    amount = data["Polls"][poll_id]["Unpaid"][name]
    del data["Polls"][poll_id]["Unpaid"][name]
    data["Polls"][poll_id]["Paid"][name] = amount

    # data = context.user_data
    # amount = data["Polls"][poll_id]["Unpaid"][name]
    # del data["Polls"][poll_id]["Unpaid"][name]
    # data["Polls"][poll_id]["Paid"][name] = amount

    inline_keyboards = []
    unpaid = data["Polls"][poll_id]["Unpaid"]
    for name in unpaid:
        inline_keyboards.append(InlineKeyboardButton(name, callback_data="/paid " + name + " " + poll_id))

    # Edit message into poll
    query.edit_message_text(
        text=generate_poll(data, poll_id),
        reply_markup=InlineKeyboardMarkup([inline_keyboards]),
        parse_mode='HTML'
    )

    # Data management
    pickle_out = open("{}.pickle".format(poll_id), "wb")
    pickle.dump(data, pickle_out)
    pickle_out.close()

# def turnOnSummary(context, poll_id):
#     print(context.user_data)
#     context.user_data["Requests"] = poll_id
#     context.job_queue.run_repeating(sendSummary, interval=10, name=poll_id)
#
# def turnOffSummary(update, context, poll_id):
#     jobs = context.job_queue.get_jobs_by_name(poll_id)
#     for job in jobs:
#         job.schedule_removal()
#
# def sendSummary(update, context):
#     print(context.user_data)
#     summary = generate_summary(context.chat_data["requests"])
#     context.bot.sendMessage(chat_id=context.user_data["user_id"], text=summary)
#
# def generate_summary(poll_id):
#     pickle_in = open("{}.pickle".format(poll_id), "rb")
#     data = pickle.load(pickle_in)
#
#     title = data["Polls"][poll_id]["Title"]
#     unpaid = len(data["Polls"][poll_id]["Unpaid"])
#     paid = len(data["Polls"][poll_id]["Paid"])
#
#     summary = "Summary of payment: " + str(title) + "\n\nPAID: " + str(paid) + "\n\nUNPAID: " + str(unpaid)
#     return summary

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    context.bot.sendMessage(chat_id=26206762, text="Error")

# First Time Login Conversation
USERNAME, PAYMENT_METHOD, LINK, READY = range(4)
PUBLISH, DELETE = range(2)
registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_username
                )
            ],
            PAYMENT_METHOD: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_payment_method
                )
            ],
            LINK: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_payment_links
                )
            ]
        },
        fallbacks=[CommandHandler('ready', ready)]
    )

# New Payment Conversation
TITLE, NAME, AMOUNT, DONE = range(4)
conv_handler = ConversationHandler(
        entry_points=[CommandHandler('new', new_payment)],
        states={
            TITLE: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_title
                )
            ],
            NAME: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_name
                )
            ],
            AMOUNT: [
                MessageHandler(
                    Filters.text & (~Filters.command), update_amount
                )
            ],
            DONE: [
                CommandHandler('done', done)
            ]

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )


def main():
	updater = Updater(token=TOKEN, use_context=True)
	dispatcher = updater.dispatcher

	dispatcher.add_handler(registration_handler)
	dispatcher.add_handler(conv_handler)
	dispatcher.add_handler(InlineQueryHandler(inlinequery))
	dispatcher.add_handler(CallbackQueryHandler(callbackhandle))
	dispatcher.add_error_handler(error)

	updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
	updater.bot.setWebhook('https://paymeplsbot.herokuapp.com/' + TOKEN)

	updater.idle()

if __name__ == '__main__':
    	main()