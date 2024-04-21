import random
import chess
import requests
import chess.svg
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from io import BytesIO

color_keyboard = [['белый', 'черный'],
                  ['случайно']]
color_markup = ReplyKeyboardMarkup(color_keyboard, one_time_keyboard=True)


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            1: [CommandHandler('new_game', new_game),
                CommandHandler('help', help_command)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_level),
                CommandHandler('help', help_command)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_color),
                CommandHandler('help', help_command),
                CommandHandler('new_game', new_game)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_move),
                CommandHandler('help', help_command),
                CommandHandler('print_board', print_board)]
        },
        fallbacks=[CommandHandler('stop', stop)]))
    application.run_polling()


async def add_color(update, context):
    context.user_data['color'] = None
    if update.message.text.lower() in ['белый', 'черный']:
        context.user_data['color'] = update.message.text.lower()
        await update.message.reply_text(f'Ваш цвет - {update.message.text.lower()}')
    elif update.message.text.lower() == 'случайно':
        c = random.choice(['белый', 'черный'])
        context.user_data['color'] = c
        await update.message.reply_text(f'Ваш цвет - {c}')
    else:
        await update.message.reply_text('Некорректный ввод. Выберите цвет: белый, черный или случайный.',
                                        reply_markup=color_markup)
    if context.user_data['color'] is None:
        return 3
    if context.user_data['color'] == 'белый':
        await update.message.reply_text('Ваш ход!')
    else:
        move = get_moves(context.user_data['fen'], context.user_data['level'])
        commit_move(move, context)
        await update.message.reply_text(move)
    return 4


async def add_level(update, context):
    if update.message.text in [str(x) for x in range(1, 6)]:
        context.user_data['level'] = update.message.text
        await update.message.reply_text(f'Выбран уровень сложности {update.message.text}.')
        await update.message.reply_text('Выберите цвет', reply_markup=color_markup)
        return 3
    else:
        await update.message.reply_text('Некорректный ввод. Выберите уровень сложности от 1 до 5.')
        return 2


async def add_move(update, context):
    board = chess.Board(context.user_data['fen'])
    move = update.message.text

    if board.is_legal(chess.Move.from_uci(move)):
        commit_move(move, context)
        move = get_moves(context.user_data['fen'], context.user_data['level'])
        commit_move(move, context)
        await update.message.reply_text(move)
    else:
        await update.message.reply_text('Некорректный ход. Чтобы посмотреть позицию, введите команду /print_board')


async def start(update, context):
    await update.message.reply_text("Привет! Давай сыграем в шахматы! Чтобы начать новую игру, напиши /new_game.")
    return 1


async def help_command(update, context):
    await update.message.reply_text("Доступные команды: "
                                    "/help"
                                    "/board")


async def print_board(update, context):
    board = chess.Board(context.user_data['fen'])
    await context.bot.send_photo(board.__str__())


async def new_game(update, context):
    context.user_data['fen'] = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    context.user_data['moves'] = []
    await update.message.reply_text("Выбери уровень сложности от 1 до 5")
    return 2


async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def get_moves(fen, level):
    json = {'fen': fen}
    response = requests.get('http://127.0.0.1/api/analysis', json=json).json()
    return response['best_move']


def commit_move(move, context):
    board = chess.Board(context.user_data['fen'])
    board.push(chess.Move.from_uci(move))
    context.user_data['fen'] = board.fen()


if __name__ == '__main__':
    main()
