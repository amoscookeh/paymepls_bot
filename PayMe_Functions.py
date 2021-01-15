from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, InlineQueryHandler, CallbackQueryHandler, DictPersistence
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from uuid import uuid4
import logging
from pymongo import MongoClient
import os

PORT = int(os.environ.get('PORT', 5000))
TOKEN = os.environ['TOKEN']
PASSWORD = os.environ['PASSWORD']
DATABASE = os.environ['DATABASE']

# For data handling
client = MongoClient("mongodb+srv://paymeplsbot:{}@paymeplsdata.ehp3q.mongodb.net/{}?retryWrites=true&w=majority".format(PASSWORD, DATABASE),ssl=True)
db = client['paymeplsdata']
collection = db['paymeplsdata']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

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

def get_user_data (update):
    user_id = update.message.from_user['id']
    return collection.find({'_id':user_id})['user_data']

# Format user_data for first time start
def format_user_data (update, context):
    user = update.message.from_user
    user_id = user['id']
    username = user['username']
    context.user_data["polls"] = {}
    context.user_data["poll count"] = 0
    context.user_data["Name"] = ""
    context.user_data["Username"] = username
    post = {'_id':user_id, 'user_data': context.user_data}
    try:
        collection.insert_one(post)
    except:
        collection.find_one_and_replace({'_id': user_id}, {'_id': user_id, 'user_data': context.user_data})

# Update username of user
def update_username (update, context):
    name = update.message.text
    name = " ".join(w.capitalize() for w in name.split())
    collection.find_one_and_update({'_id': update.message.from_user['id']}, {'$set':{'user_data.Name':name, 'user_data.payment methods': {}}})
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text= "Nice to meet you " + name + "! \nNow, how would you like others to pay you? (Eg. Bank Transfer, PayNow, PayPal, etc.)")
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text= "or press /ready if that's all!")
    return PAYMENT_METHOD

# Update list of payment methods
def update_payment_method (update, context):
    method = update.message.text
    collection.find_one_and_update({'_id': update.message.from_user['id']}, {'$set': {'user_data.payment methods.{}'.format(method): {}}})
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Nice, now provide me some information that's linked to {}! (Eg. Link, Acc. Number, etc.)".format(method))
    return LINK

# Update list of payment method information
def update_payment_links (update, context):
    info = update.message.text
    user_data = collection.find({'_id': update.message.from_user['id']})[0]['user_data']
    method = list(user_data['payment methods'])[-1]
    collection.find_one_and_update(
        {'_id': update.message.from_user['id']},
        {'$set': {'user_data.payment methods.{}'.format(method): info}}
    )
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Alright, now provide me with another payment method (Eg. Bank Transfer, PayNow, PayLah!, etc.) \n\nor press /ready if that's all!")
    return PAYMENT_METHOD

# When user is done with registration
def ready (update, context):
    try:
        data = collection.find({'_id': update.message.from_user['id']})[0]['user_data']
    except:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Sorry, your data is invalid, try again with <b>/start</b>",
                                 parse_mode='html')
        return registration_handler.END

    mesg = "<b>Name:</b> " + data["Name"] + "\n<b>Payment Method</b> : Information"
    try:
        for method in data["payment methods"]:
            mesg += "\n<b>" + method + " : </b>" + data["payment methods"][method]
    except:
        mesg += "-NIL-"
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Thank you for providing me with this information! The information you have provided me with is as follows:\n\n" + mesg,
                             parse_mode='html')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="If this information is correct, proceed by using /new to create a new payment! \nOr, use /start to restart registration")
    return registration_handler.END

def cancel_reg (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Data erased. Use /start to restart bot!")
    format_user_data(update,context)
    return registration_handler.END

# Create a new payment poll
def new_payment (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome back!" +
                                                                    "\nEnter your title of payment:")

    return TITLE

# Update title of payment poll
def update_title (update, context):
    title = update.message.text
    user_id = update.message.from_user['id']
    poll_id = "{}-{}".format(user_id, collection.find({'_id':user_id})[0]['user_data']['poll count'])

    new_poll = {"Title": title, "Unpaid": {}, "Paid": {}, "Message": 0}
    collection.update(
        {'_id': user_id},
        {'$set': {'user_data.polls.{}'.format(poll_id): new_poll}}
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text="New Payment: " + title)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Nice! Now who owes you money?")

    return NAME

# Add name to payment poll
def update_name (update, context):
    user_id = update.message.from_user['id']
    poll_id = "{}-{}".format(user_id, collection.find({'_id': user_id})[0]['user_data']['poll count'])

    name = update.message.text
    name = " ".join(w.capitalize() for w in name.split())

    collection.update(
        {'_id': user_id},
        {'$set': {'user_data.polls.{}.Unpaid.{}'.format(poll_id, name): 0}}
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text="How much does this person owe you?")

    return AMOUNT

# Ass amount of money previous added name owes
def update_amount (update, context):
    amount = update.message.text
    user_id = update.message.from_user['id']
    poll_id = "{}-{}".format(user_id, collection.find({'_id': user_id})[0]['user_data']['poll count'])
    name = list(collection.find({'_id': user_id})[0]['user_data']['polls'][poll_id]['Unpaid'].keys())[-1]

    try:
        amount = float(amount)
    except:
        update.message.reply_text(
            "Sorry, that was an invalid amount, please try again!"
        )
        return AMOUNT

    collection.update(
        {'_id': user_id},
        {'$set': {'user_data.polls.{}.Unpaid.{}'.format(poll_id, name): amount}}
    )

    update.message.reply_text(
        "Well done! Continuing adding names or press /done if you're done!"
    )

    return NAME

# When user is done with poll
def done (update, context):
    user_data = collection.find({'_id': update.message.from_user['id']})[0]['user_data']
    polls = user_data['polls']

    collection.update(
        {'_id': update.message.from_user['id']},
        {'$inc': {'user_data.poll count': 1}}
    )

    poll_id = list(polls)[-1]
    poll = generate_poll(user_data, poll_id)

    inline_keyboard = [
        [
            InlineKeyboardButton("Publish Payment", switch_inline_query=""),
            InlineKeyboardButton("Delete Payment", callback_data="/dltpoll " + poll_id)
        ]
    ]

    message = update.message.reply_html(
        text=poll,
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )

    collection.update(
        {'_id': update.message.from_user['id']},
        {'$set': {'user_data.polls.{}.Message'.format(poll_id): message.message_id}}
    )

    return ConversationHandler.END

def cancel (update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Payment erased. Use /new to create a new payment poll!")
    polls = collection.find({'_id': update.message.from_user['id']})['user_data']['polls']
    del polls[list(polls)[-1]]
    collection.find_one_and_replace({'_id': 'polls'}, polls)
    return conv_handler.END

# Poll text generator
def generate_poll (user_data, poll_id):
    title = user_data["polls"][poll_id]["Title"]
    unpaid = user_data["polls"][poll_id]["Unpaid"]
    paid = user_data["polls"][poll_id]["Paid"]
    methods = user_data["payment methods"]

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
    data = query['data'].split('|')
    command = data[0]
    if command == "/dltpoll":
        query.answer("Payment Deleted")
        dltpoll(update, context, data[1])
    elif command == "/paid":
        query.answer("Payment confirmed")
        paid(update, context, data[1], data[2])

# Delete poll from user data
def dltpoll (update, context, poll_id):
    user_id = int(poll_id.split('-')[0])
    polls = collection.find({'_id': user_id})[0]['user_data']['polls']
    poll_to_dlt = list(polls.keys())[-1]

    # Delete message
    message = polls[poll_to_dlt]['Message']
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=message
    )

    # Delete Data
    polls.pop(poll_to_dlt)
    print(polls)
    collection.update(
        {'_id': user_id},
        {'$set': {'user_data.polls': polls}}
    )
    collection.update(
        {'_id': user_id},
        {'$inc': {'user_data.poll count': -1}}
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text="Payment deleted!")

# Options to post existing polls
def inlinequery(update, context):
    results = generate_inline_queries(update, context)
    update.inline_query.answer(results)

# Generate a list of inline queries
def generate_inline_queries(update,context):
    user_data = collection.find({'_id': update.inline_query.from_user['id']})[0]['user_data']
    polls = user_data['polls']

    poll_ids = list(polls.keys())  # Empty dictionaries in Python return false when bool(dict)

    inline_queries = []
    for poll_id in poll_ids:
        inline_keyboards = []
        title = polls[poll_id]["Title"]
        for name in polls[poll_id]["Unpaid"]:
            inline_keyboards.append(InlineKeyboardButton(name, callback_data="/paid|" + name + "|" + poll_id))
        query = InlineQueryResultArticle(id=uuid4(), title=title,
                                         input_message_content=InputTextMessageContent(generate_poll(user_data, poll_id), parse_mode='HTML'),
                                         reply_markup=InlineKeyboardMarkup([inline_keyboards]),
                                         thumb_url='https://raw.githubusercontent.com/amoscookeh/paymepls_bot/main/Paymeplslogo.jpg'
                                         )
        inline_queries.append(query)

    return inline_queries

def paid(update, context, name, poll_id):
    query = update.callback_query
    user_id = poll_id.split('-')[0]

    user_data = collection.find({'_id': int(user_id)})[0]['user_data']
    poll = user_data['polls'][poll_id]

    amount = poll["Unpaid"][name]
    poll["Unpaid"].pop(name)
    poll["Paid"][name] = amount
    collection.find_one_and_update(
        {'_id': int(user_id)},
        {'$set': {'user_data.polls.{}'.format(poll_id): poll}}
    )

    inline_keyboards = []
    unpaid = poll["Unpaid"]
    for name in unpaid:
        inline_keyboards.append(InlineKeyboardButton(name, callback_data="/paid|" + name + "|" + poll_id))

    new_user_data = collection.find({'_id': int(user_id)})[0]['user_data']

    # Edit message into poll
    query.edit_message_text(
        text=generate_poll(new_user_data, poll_id),
        reply_markup=InlineKeyboardMarkup([inline_keyboards]),
        parse_mode='HTML'
    )

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# First Time Login Conversation
USERNAME, PAYMENT_METHOD, LINK = range(3)
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
    fallbacks=[CommandHandler('ready', ready)],
    conversation_timeout=300
)

# New Payment Conversation
TITLE, NAME, AMOUNT = range(3)
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
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('done', done)],
    conversation_timeout=300
)

def main():
    # Persistence testing
    dict_persistence = DictPersistence()

    updater = Updater(token=TOKEN, persistence=dict_persistence, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(registration_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(InlineQueryHandler(inlinequery))
    dispatcher.add_handler(CallbackQueryHandler(callbackhandle))

    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook('https://paymeplsbot.herokuapp.com/' + TOKEN)

    updater.idle()

if __name__ == '__main__':
    main()
