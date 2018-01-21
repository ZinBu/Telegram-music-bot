import json
import random
import os

import telebot

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "//"
MUSIC_BASE = THIS_FOLDER + "music_base.json"
USERS_BASE = THIS_FOLDER + "Users_base.json"
LEADERBOARD_BASE = THIS_FOLDER + "leaderboard.json"


def save_base(data):
    """ Загрузка музыки в базу """
    with open(MUSIC_BASE, 'w') as f:
        json.dump(data, f)


def load_base():
    """ Загрузка музыки из базы """
    with open(MUSIC_BASE, 'r') as f:
        base = json.load(f)
    return base


def save_new_user(user_id, correct_answer, track_number):
    """ Создание сессии с новым игроком """
    # если файл существует
    try:
        # выгружаем
        with open(USERS_BASE, 'r') as f:
            data = json.load(f)

        # если уже есть id пользователя/если нет
        if str(user_id) in data.keys():
            data[str(user_id)]["answer"] = correct_answer
            data[str(user_id)]["tracks"].append(track_number)
        else:
            data.update({user_id: {"answer": correct_answer, "points": 0, "tracks": [track_number]}})

        # загружаем обратно
        with open(USERS_BASE, 'w') as f:
            json.dump(data, f)

    # если файл не существует
    except FileNotFoundError:
        with open(USERS_BASE, 'w') as f:
            data = {user_id: {"answer": correct_answer, "points": 0, "tracks": [track_number]}}
            json.dump(data, f)


def load_user(user_id):
    """ Загрузка сессии уже имеющегося игрока """
    try:
        with open(USERS_BASE, 'r') as f:
            base = json.load(f)
            user = base.get(str(user_id))
            if user:
                answer = user["answer"]
                score = user["points"]
                tracks = user["tracks"]
                return answer, score, tracks
            else:
                return
    except FileNotFoundError:
        return


def update_user_score(user_id, score):
    """ Обновление очков игрока """
    with open(USERS_BASE, 'r') as f:
        data = json.load(f)

    data[str(user_id)]["points"] = score
    with open(USERS_BASE, 'w') as f:
        json.dump(data, f)


def delete_user(user_id):
    """ Удаление сессии игрока """
    with open(USERS_BASE, 'r') as f:
        data = json.load(f)

    data.pop(str(user_id))
    with open(USERS_BASE, 'w') as f:
        json.dump(data, f)


def update_leaderboard(user_score, user_name, user_id):
    """ Проверка счета игрока и сохранение в таблицу лидеров """

    user_id = str(user_id)
    user_score = int(user_score)
    try:
        # Открываем доску лидеров
        with open(LEADERBOARD_BASE, 'r') as f:
            base = json.load(f)
        # Определяем минимальный счет на доске
        min_score = min([int(base[key][1]) for key in base.keys()])
        # устанавливаем максимальную длину таблицы
        board_length = 5

        # если счет игрока больше минимального на доске
        if user_score > min_score:
            # если новый рекордсмен
            if user_id not in base.keys():
                base.update({user_id: (user_name, user_score)})
                # удаляем слабака из базы, если она заполнена
                if len(base) > board_length:                    
                    # Сортируем по убыванию очков и получаем id лузера
                    looser = sorted([(key, base[key][1]) for key in base.keys()],
                                                   key=lambda x: int(x[1]),
                                                   reverse = True)[-1][0]
                    base.pop(looser)
            # если он уже есть в таблице рекордов - обновляем его счет
            else:
                # если новый счет больше старого, то обновляем
                if base[user_id][1] < user_score:
                    base[user_id][1] = user_score

            # пересохраняем
            with open(LEADERBOARD_BASE, 'w') as f:
                json.dump(base, f)

        # если доска не заполнена до конца
        elif int(user_score) <= int(min_score) and len(base) < board_length:
            # если новый рекордсмен
            if user_id not in base.keys():
                base.update({user_id: (user_name, user_score)})
            # если он уже есть в таблице рекордов - обновляем его счет
            else:
                # если новый счет больше старого, то обновляем
                if base[user_id][1] < user_score:
                    base[user_id][1] = user_score

            # пересохраняем
            with open(LEADERBOARD_BASE, 'w') as f:
                json.dump(base, f)

    except FileNotFoundError:
        with open(LEADERBOARD_BASE, 'w') as f:
            json.dump({user_id: (user_name, user_score)}, f)


def load_leaderboard():
    """
    Загрузка таблицы лидеров
    :return: dict - вида {user_score: (user_name, user_id), ...}
    """
    try:
        # Пытаемся вернуть не пустую таблицу лидеров
        with open(LEADERBOARD_BASE, 'r') as f:
            base = json.load(f)
            if base:
                return base
            else:
                return
    except FileNotFoundError:
        return


def isrussian(word):
    """ Проверка: является ли слово русским """
    pattern = ['а', 'б', 'в', 'г', 'д', 'е', 'ж', 'з',
               'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п',
               'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч',
               'ш', 'щ', 'ъ', 'э', 'ю', 'я']

    for s in pattern:
        if s in word.lower():
            return True
    return False


def generate_wrong_answers(all_base):
    """
    Создание 3 неправильных ответа для каждой композиции
    :param all_base: Словарь с данными вида {1: {'id': 123, 'correct': answer}}
    :return: Такой же словарь как на входе, только с тройкой неправильных
             вариантов для каждой записи
    """
    # Получение списка всех имеющихся ответов
    all_answers = [x["correct"] for x in all_base.values()]
    # Перемешиваем
    random.shuffle(all_answers)

    # Русские варианты
    answers_rus = [x for x in all_answers if isrussian(x)]
    # Зарубежные
    answers_eng = [x for x in all_answers if not isrussian(x)]

    # добавление по 3 неверных ответа к каждой записи
    for row in all_base.keys():
        wrong_answers = []
        while len(wrong_answers) != 3:
            # определяем язык названия и исполнителя трека
            if isrussian(all_base[row]["correct"]):
                # выбираем вариант случайным образом среди русских треков
                wrong_answer = random.choice(answers_rus)
            else:
                # выбираем вариант случайным образом среди зарубежных треков
                wrong_answer = random.choice(answers_eng)
            # Если ответ не совпадает с правильным ответом текущей песни - записываем
            if wrong_answer != all_base[row]["correct"] and wrong_answer not in wrong_answers:
                wrong_answers.append(wrong_answer)

        # создание строки неправильных ответов (для совместимости функций)
        wrong_answers = "{},{},{}".format(wrong_answers[0], wrong_answers[1], wrong_answers[2])
        all_base[row]["wrong"] = wrong_answers
    return all_base


def generate_markup(right_answer, wrong_answers):
    """
    Создаем кастомную клавиатуру для выбора ответа
    :param right_answer: Правильный ответ
    :param wrong_answers: Набор неправильных ответов
    :return: Объект кастомной клавиатуры
    """
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # Склеиваем правильный ответ с неправильными
    all_answers = '{},{}'.format(right_answer, wrong_answers)
    # Создаем лист (массив) и записываем в него все элементы
    list_items = [x for x in all_answers.split(',')]
    # Перемешиваем все элементы
    random.shuffle(list_items)
    # Заполняем разметку перемешанными элементами
    for item in list_items:
        markup.add(item)
    return markup


def show_leaderboard():
    """ Загрузка доски игроков и ее форматированный вывод """

    # Загружаем доску игроков
    leaders_base = load_leaderboard()
    if leaders_base:
        # Сортируем по убыванию очков
        sorted_data = sorted([(leaders_base[key][0], leaders_base[key][1]) for key in leaders_base.keys()],
                             key=lambda x: int(x[1]),
                             reverse = True)
        # Формируем строку лидеров для вывода
        leaders = ''
        for i in enumerate(sorted_data):
            leaders += "{} место: {} - {}\n".format(i[0]+1, i[1][0], i[1][1])
        return leaders
    else:
        return


if __name__ == '__main__':
    # bb = load_base()
    # print(len(bb))
    # for i in range(len(bb)):
    #     print(i+1, bb[str(i+1)])

    # Пересоздать текущую базу музыки с генерацией новых ответов
    # save_base(generate_wrong_answers(bb))

    # print(load_leaderboard())
    # update_leaderboard(user_score='11', user_name='Grisha', user_id='37578679')
    # print(load_leaderboard())
    print(show_leaderboard())