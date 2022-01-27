import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME: int = 6
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
_log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# _log_format: str = (
#     '%(asctime)s - %(levelname)s - %(funcName)s - %(name)s  - %(message)s')
stream_logger = logging.StreamHandler(stream=sys.stdout)
stream_logger.setLevel(level=logging.INFO)
stream_logger.setFormatter(_log_format)
logger.addHandler(stream_logger)
# stream_logger = logging.StreamHandler(stream=sys.stdout)
# stream_logger.setLevel(logging.INFO)
# stream_logger.setFormatter(logging.Formatter(_log_format))

# logger = logging.getLogger(__name__)
# logger.addHandler(stream_logger)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщений в телеграмм."""
    logging.info('Отправка сообщения пользователю')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к единственному эндпоинту Яндекс.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params)
    logging.info('Запрос к серверу Яндекс.Домашка')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка! Ответ сервер - {response.status_code}')
        raise Exception(f'Ошибка! Ответ сервер - {response.status_code}')
    return response.json()


def check_response(response: dict) -> list:
    """Функция проверяет ответ API на корректность."""
    if not response:
        logging.error(
            f'Ответ от API содержит пустой словарь response {response}')
        raise Exception(
            f'Ответ от API содержит пустой словарь response {response}')

    if not isinstance(response, dict):
        logging.error('Ошибка типа ответа от сервера')
        raise TypeError('Ошибка типа ответа от сервера')

    homework = response.get('homeworks')

    if homework is None:
        logging.error('Отсутствует ключ "homeworks" в словаре response')
        raise KeyError('Отсутствует ключ "homeworks" в словаре response')

    if not isinstance(homework, list):
        logging.error('Данные ключа "homeworks" не являются списком')
        raise Exception('Данные ключа "homeworks" не являются списком')

    return homework


def parse_status(homework: list) -> str:
    """Функция извлекает получает статус домашней работы."""
    if homework:
        if isinstance(homework, list):
            homework = homework[0]

        homework_status = homework.get('status')
        if homework_status is None:
            logging.error('Отсутствует ключ "status" в словаре homework')
            raise KeyError('Отсутствует ключ "status" в словаре homework')

        homework_name = homework.get('homework_name')
        if homework_name is None:
            logging.error(
                'Отсутствует ключ "homework_name" в словаре homework')
            raise KeyError(
                'Отсутствует ключ "homework_name" в словаре homework')

        verdict = HOMEWORK_STATUSES.get(homework_status)
        if verdict is None:
            logging.error('Не известный статус домашней работы')
            raise KeyError('Не известный статус домашней работы')

        return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    return 'В настоящее время у Вас нет работ на проверке'


def check_tokens() -> bool:
    """Функция проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logging.critical(
            f'Отсутствует переменная окружения: {PRACTICUM_TOKEN}')
        return False
    if TELEGRAM_TOKEN is None:
        logging.critical(
            f'Отсутствует переменная окружения: {TELEGRAM_TOKEN}')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.critical(
            f'Отсутствует переменная окружения: {TELEGRAM_CHAT_ID}')
        return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    if check_tokens():
        current_answer: str = ''
        current_error: str = ''
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp: int = int(time.time())

        while True:
            try:
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                answer = parse_status(homework)
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                if current_error != message:
                    send_message(bot, message)
                    current_error = message
                time.sleep(RETRY_TIME)
            else:
                if answer != current_answer:
                    send_message(bot, answer)
                    current_answer = answer

    raise Exception('Не удалось получить переменные окружения')


if __name__ == '__main__':
    main()
