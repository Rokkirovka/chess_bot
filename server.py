import random

import chess
import chess.svg
import requests
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

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
                CommandHandler('print_board', print_board),
                CommandHandler('analysis', analysis),
                CommandHandler('tip', tip),
                CommandHandler('surrender', surrender)],
            5: [CommandHandler('help', help_command),
                CommandHandler('new_game', new_game)]
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

    try:
        if board.is_legal(chess.Move.from_uci(move)):
            commit_move(move, context)
            board = chess.Board(context.user_data['fen'])
            if board.is_checkmate():
                await update.message.reply_text('Мат! Вы хорошо сыграли!')
                await update.message.reply_text('Если хотите сыграть ещё, напишите\n/new_game')
                return 5
            elif board.is_stalemate():
                await update.message.reply_text('Пат. Ничья!')
                await update.message.reply_text('Если хотите сыграть ещё, напишите\n/new_game')
                return 5
            move = get_moves(context.user_data['fen'], context.user_data['level'])
            commit_move(move, context)
            board = chess.Board(context.user_data['fen'])
            await update.message.reply_text(move)
            if board.is_checkmate():
                await update.message.reply_text('Шах и мат!')
                await update.message.reply_text('Если хотите сыграть ещё, напишите\n/new_game')
                return 5
            elif board.is_stalemate():
                await update.message.reply_text('Пат. Ничья!')
                await update.message.reply_text('Если хотите сыграть ещё, напишите\n/new_game')
                return 5
            elif board.is_check():
                await update.message.reply_text('Вам шах!')
        else:
            await update.message.reply_text('Некорректный ход. Чтобы посмотреть позицию, введите команду\n/print_board')
    except ValueError:
        await update.message.reply_text('Неверно введен ход. Чтобы сходить, введите сначала начальную '
                                        'клетку, а затем клетку, в которую вы хотите пойти.\nНапример: e2e4\n'
                                        'Если вы ходите пешкой на последнюю горизонталь и хотите провести фигуру, '
                                        'То после хода напишите символ фигуры.\nНапример: e7e8q')


async def start(update, context):
    await update.message.reply_text("Привет! Давай сыграем в шахматы! Чтобы начать новую игру, напиши\n/new_game")
    return 1


async def help_command(update, context):
    await update.message.reply_text("Доступные команды:\n"
                                    "/help\n"
                                    "/start\n"
                                    "Во время партии:\n"
                                    "/print_board - нарисовать доску\n"
                                    "/tip - подсказка\n"
                                    "/analysis - анализ партии\n"
                                    "/surrender - сдаться")


async def print_board(update, context):
    board = chess.Board(context.user_data['fen'])
    await update.message.reply_text(board.__str__().replace('.', ' '))


async def tip(update, context):
    move = get_moves(context.user_data['fen'], 5)
    await update.message.reply_text(f'Лучший ход в данной позиции - {move}')


async def surrender(update, context):
    await update.message.reply_text('Ты сделал все, что мог, и это уже большая победа.')
    return 5


async def analysis(update, context):
    json = {'fen': context.user_data['fen'], 'depth': 5}
    response = requests.get('http://127.0.0.1:5000/api/analysis', json=json).json()
    score = response['score']
    if '#' in score:
        if '+' in score:
            await update.message.reply_text(f'Белые могут поставить мат в {score[2:]} ходов.')
        else:
            await update.message.reply_text(f'Черные могут поставить мат в {score[2:]} ходов.')
    else:
        if '+' in score:
            await update.message.reply_text(f'У белых преимущество на {int(score[1:]) / 100} сантипешек.')
        else:
            await update.message.reply_text(f'У черных преимущество на {int(score[1:]) / 100} сантипешек.')


async def new_game(update, context):
    context.user_data['fen'] = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    context.user_data['moves'] = []
    await update.message.reply_text("Выбери уровень сложности от 1 до 5")
    return 2


async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def get_moves(fen, level):
    json = {'fen': fen, 'depth': level}
    response = requests.get('http://127.0.0.1:5000/api/analysis', json=json).json()
    return response['best_move']


def commit_move(move, context):
    board = chess.Board(context.user_data['fen'])
    board.push(chess.Move.from_uci(move))
    context.user_data['fen'] = board.fen()


if __name__ == '__main__':
    main()
