import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (RequestError, UnexpectedStatusError,
                        WrongResponseError, WrongStatusCodeError)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('YOUR_TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('YOUR_PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('YOUR_TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    environment_variables = {
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    missed_vars = []
    for var in environment_variables:
        if environment_variables[var] is None:
            missed_vars.append(var)
    if missed_vars == []:
        logging.debug(
            'Все переменные окружения указаны. Программа готова к работе.'
        )
    else:
        logging.critical(
            f'Не указаны обязательные переменные окружения: {missed_vars}!'
            'Программа принудительно остановлена.'
        )
        sys.exit(1)


def send_message(bot, message):
    """Отправляет сообщение в нужный telegram чат."""
    logging.debug('Попытка отправки сообщения.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logging.error('Ошибка при отправке сообщения.', exc_info=True)
    else:
        logging.debug('Сообщение успешно отправлено.')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервису."""
    logging.debug(
        f'Запрос к API. Адрес ресурса: {ENDPOINT}.'
        'Метод запроса: GET.'
    )
    payload = {'from_date': (timestamp)}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise RequestError(
            f'Ошибка при отправке запроса: {error}.'
            f'Адрес ресурса: {ENDPOINT}.'
            'Метод запроса: GET.'
        )
    if response.status_code != 200:
        raise WrongStatusCodeError(
            f'Запрос к адресу: {ENDPOINT}.'
            'Метод запроса: GET.'
            f'Статус ответа: {response.status_code}. '
            'Ожидаемый код: 200'
        )
    try:
        response.json()
    except Exception as error:
        raise WrongResponseError(
            'API вернул неверный json! Oтвет: '
            f'{response.text}, ошибка: {error}'
        )
    logging.debug(
        f'Запрос к API успешно совершен.'
        f'Адрес ресурса: {ENDPOINT}.'
        'Метод запроса: GET.'
    )
    return response.json()


def check_response(response):
    """Проверяет полученный от API ответ на соответствие документации."""
    logging.debug('Начало проверки полученных от API данных.')
    if isinstance(response, dict) is False:
        raise TypeError(
            f'Тип полученных данных: {type(response)}. '
            'Ожидаемый тип данных: dict.'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'В ответе API отсутствует ожидаемый ключ:'
            '"homeworks".'
        )
    if 'current_date' not in response:
        raise KeyError(
            'В ответе API отсутствует ожидаемый ключ:'
            '"current_date".'
        )
    if isinstance(response['homeworks'], list) is False:
        raise TypeError(
            f'Тип полученных данных: {type(response["homeworks"])}. '
            'Ожидаемый тип данных: list.'
        )
    else:
        logging.debug('Данные успешно прошли проверку.')


def parse_status(homework):
    """Извлекает из конкретной работы ее статус."""
    logging.debug('Начало проверки обновления статуса работы.')
    if type(homework) is not dict:
        raise TypeError(
            f'Получен неправильный тип для homework: {type(homework)} '
            'Ожидаемый тип данных: dict.'
        )
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе API отсутствуют ожидаемые ключи:'
            '"homework_name".'
        )
    if 'status' not in homework:
        raise KeyError(
            'В ответе API отсутствуют ожидаемые ключи:'
            '"status".'
        )
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise UnexpectedStatusError(
            'Получен неожиданный статус домашней работы: '
            f'{homework["status"]}.'
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.debug('Проверка статуса работы прошла успешно. Статус обновился.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response['current_date']
            if response['homeworks']:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Статус работы не обновился.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
            sent_msg = ''
            if message != sent_msg:
                send_message(bot, message)
                sent_msg = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler(
                'main.log',
                mode='w',
                encoding='UTF-8',
                delay=False
            ),
        ],
        format=(
            '%(asctime)s, %(levelname)s, %(funcName)s,'
            '%(lineno)d, %(message)s'
        )
    )
    main()
