import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

from exceptions import (
    RequestError,
    UnexpectedStatusError,
    WrongResponseError,
    WrongStatusCodeError,
    WrongKeyError
)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s',
    encoding='UTF-8',
)

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
    environment_variables = (
        TELEGRAM_TOKEN,
        PRACTICUM_TOKEN,
        TELEGRAM_CHAT_ID
    )
    for variable in environment_variables:
        if variable is None:
            logging.critical(
                f'Не указана обязательная переменная окружения: {variable}!'
                'Программа принудительно остановлена.'
            )
            sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в нужный telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено.')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервису."""
    try:
        payload = {'from_date': (timestamp)}
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        raise RequestError(f'Ошибка при отправке запроса: {error}')
    if response.status_code != 200:
        raise WrongStatusCodeError(
            f'Статус ответа: {response.status_code}. '
            'Ожидаемый код: 200'
        )
    try:
        data = response.json()
    except Exception as error:
        raise WrongResponseError(
            f'API вернул неверный json! Oтвет: '
            f'{response.text}, ошибка: {error}'
        )
    return data


def check_response(response):
    """Проверяет полученный от API ответ на соответствие документации."""
    if type(response) is not dict:
        raise TypeError(
            f'Тип полученных данных: {type(response)}, '
            'Ожидаемый тип данных: dict.'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'В ответе API отсутствует ожидаемый ключ:'
            '"homeworks".'
        )
    if type(response['homeworks']) is not list:
        raise TypeError(
            'Получен неправильный тип данных. '
            'Ожидаемый тип данных: list.'
        )


def parse_status(homework):
    """Извлекает из конкретной работы ее статус."""
    if type(homework) is not dict:
        raise TypeError(
            f'Получен неправильный тип для homework: {type(homework)} '
            'Ожидаемый тип данных: dict.'
        )
    if 'homework_name' not in homework:
        raise WrongKeyError(
            'В ответе API отсутствуют ожидаемые ключи:'
            '"homework_name".'
        )
    if 'status' not in homework:
        raise WrongKeyError(
            'В ответе API отсутствуют ожидаемые ключи:'
            '"status".'
        )
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise UnexpectedStatusError(
            'Получен неожиданный статус домашней работы: '
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS[homework_status]
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
            if response['homeworks']:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                send_message(bot, message)
                timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
