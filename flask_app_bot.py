import flask
import telebot
import logging
import config
import os, time, random
import utils


# Configs
API_TOKEN = config.token
WEBHOOK_URL_BASE = "https://%s" % (config.host)
WEBHOOK_URL_PATH = "/%s/" % (API_TOKEN)

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "//"
MUSIC_PATH = THIS_FOLDER + 'music/'

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s',
                    level = logging.DEBUG, filename = u'mylog.log')
random.seed()

bot = telebot.TeleBot(API_TOKEN, threaded=False)

# Удаление webhook на всякий пожарный
bot.remove_webhook()
# Установка webhook
bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH)

app = flask.Flask(__name__)


@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'Hi, mister'


# обрабатываем вызовы webhook
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


@bot.message_handler(commands=['upload'])
def find_file_ids(message):
    data = {}
    count = 1
    for file in os.listdir(MUSIC_PATH):
        if file.split('.')[-1] == 'mp3':
            with open(MUSIC_PATH+file, 'rb') as f:
                msg = bot.send_audio(message.chat.id, f, performer='Sample', title='Sample')
                # добавляем в словарь информацию о трэке
                data.update({count: {"file_id": msg.voice.file_id, "correct": file[:-4]}})
                count += 1
        time.sleep(2)
    # создаем неправильные варианты ответов для каждой строки данных
    processed_data = utils.generate_wrong_answers(data)
    # сохраняем загруженное в базу
    utils.save_base(processed_data)
    # print("Done!")
    bot.send_message(message.chat.id, 'Все загружено!')


@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    # Загружаем доску игроков
    leaders = utils.show_leaderboard()
    if leaders:
        # отсылаем пользователю
        bot.send_message(message.chat.id, leaders)
    else:
        bot.send_message(message.chat.id,
                         "Похоже еще нет лидеров. Вы можете быть первым!! :)")


@bot.message_handler(commands=['game'])
def game(message, chat_id=None, tracks=None):
    # Загружаем базу музыки
    db = utils.load_base()
    random_number = random.randint(1, len(db))

    # для игрока, который в сессии
    if not chat_id:
        # Получаем случайную строку из БД
        row = db.get(str(random_number))
        # Формируем разметку
        markup = utils.generate_markup(row["correct"], row["wrong"])
        # Отправляем аудиофайл с вариантами ответа
        bot.send_audio(message.chat.id, row["file_id"], reply_markup=markup)
        # Записываем юзера в игроки и запоминаем что он должен ответить
        utils.save_new_user(message.chat.id, row["correct"], random_number)
    # для нового игрока
    else:
        # Если все имеющиеся трэки были проиграны, нужно закончить игру
        if len(db) == len(tracks):
            # Убераем клавиатуру с вариантами ответа.
            keyboard_hider = telebot.types.ReplyKeyboardRemove()
            bot.send_message(chat_id,
                             'Вы абсолютный чемпион! Весь музыкальный репертуар кончился'+
                             '\nСыграем снова?? /game'+
                             '\nПосмотреть список лидеров: /leaderboard',
                             reply_markup=keyboard_hider)
            # Удаляем юзера из хранилища (игра закончена)
            utils.delete_user(chat_id)

        # Иначе продолжаем
        else:
            # Получаем случайную и неповторяющуюся строку из БД
            while random_number in tracks:
                random_number = random.randint(1, len(db))

            row = db.get(str(random_number))
            try:
                # Формируем разметку
                markup = utils.generate_markup(row["correct"], row["wrong"])
                # Отправляем аудиофайл с вариантами ответа
                bot.send_audio(chat_id, row["file_id"], reply_markup=markup)
                # Записываем юзера в игроки и запоминаем что он должен ответить
                utils.save_new_user(chat_id, row["correct"], random_number)
            except Exception as e:
                logging.error("Косяк markup")
                print(e, "Косяк markup", row)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_answer(message):
    user_info = utils.load_user(message.chat.id)
    # Если None:
    if not user_info:
        bot.send_message(message.chat.id,
                         'Чтобы начать игру, выберите команду /game'+
                         '\nПосмотреть список лидеров: /leaderboard')
    else:
        answer = user_info[0]
        score = user_info[1]
        tracks = user_info[2]
        # Убераем клавиатуру с вариантами ответа.
        keyboard_hider = telebot.types.ReplyKeyboardRemove()
        # Если ответ правильный/неправильный
        if message.text == answer:
            score += 1
            bot.send_message(message.chat.id, 'Верно! Ваши очки: {}.  Играем дальше!!'.format(score),
                             reply_markup=keyboard_hider)
            # увеличиваем счет, делаем апдейт профиля и готовим новый вопрос
            utils.update_user_score(message.chat.id, score)
            game(None, chat_id=message.chat.id, tracks=tracks)
        else:
            bot.send_message(message.chat.id,
                             'Вы не угадали. Набранные очки: {}!\nСыграем снова?? /game'.format(score)+
                             '\nВозможно Вы новый чемпион! Посмотрим?: /leaderboard',
                             reply_markup=keyboard_hider)
            try:
                utils.update_leaderboard(score, message.from_user.first_name, message.chat.id)
            except Exception:
                pass
            # Удаляем юзера из хранилища (игра закончена)
            utils.delete_user(message.chat.id)

if __name__ == '__main__':
    app.run()