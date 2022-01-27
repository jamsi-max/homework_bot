import logging
from logging import StreamHandler, Formatter
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

_log_format: str = (
    '%(asctime)s - %(levelname)s - %(funcName)s - %(name)s  - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt=_log_format))
logger.addHandler(handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщений в телеграмм."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к серверу Яндекс.Домашка и проверка статуса ответа."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params)
    if response.status_code != HTTPStatus.OK:
        raise Exception(f'Ошибка! Ответ сервер - {response.status_code}')
    return response.json()


def check_response(response: dict) -> list:
    """Функция проверяет ответ API на корректность."""
    if not response:
        raise Exception(
            f'Ответ от API содержит пустой словарь response {response}')

    if not isinstance(response, dict):
        raise TypeError('Ошибка типа ответа от сервера')

    homework = response.get('homeworks')

    if homework is None:
        raise KeyError('Отсутствует ключ "homeworks" в словаре response')

    if not isinstance(homework, list):
        raise Exception('Данные ключа "homeworks" не являются списком')

    return homework


def parse_status(homework: list) -> str:
    """Функция извлекает получает статус домашней работы."""
    if homework:
        if isinstance(homework, list):
            homework = homework[0]

        homework_status = homework.get('status')
        if homework_status is None:
            raise KeyError('Отсутствует ключ "status" в словаре homework')

        homework_name = homework.get('homework_name')
        if homework_name is None:
            raise KeyError(
                'Отсутствует ключ "homework_name" в словаре homework')

        verdict = HOMEWORK_STATUSES.get(homework_status)
        if verdict is None:
            raise KeyError('Не известный статус домашней работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    logger.debug('В ответе отсутствуют новые статуы')
    return 'В настоящее время у Вас нет работ на проверке'


def check_tokens() -> bool:
    """Функция проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN is None:
        logger.critical(
            'Отсутствует переменная окружения: PRACTICUM_TOKEN')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical(
            'Отсутствует переменная окружения: TELEGRAM_TOKEN')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical(
            'Отсутствует переменная окружения: TELEGRAM_CHAT_ID')
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
                logger.info(
                    f'Запрос к серверу - {ENDPOINT}'
                )
                homework = check_response(response)
                logger.info(
                    'Поверка ответа получение списка домашних работ'
                )
                answer = parse_status(homework)
                logger.info(
                    'Получение статуса домашней работы и подготовкуа ответа'
                )
                current_timestamp = response.get('current_date')
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logger.error(f'Сбой в работе программы: - {error}')
                if current_error != message:
                    send_message(bot, message)
                    logger.info(
                        f'Отправка ошибки пользователю - {TELEGRAM_CHAT_ID}'
                    )
                    current_error = message
                time.sleep(RETRY_TIME)
            else:
                if answer != current_answer:
                    send_message(bot, answer)
                    logger.info(
                        f'Отправка сообщения пользователю - {TELEGRAM_CHAT_ID}'
                    )
                    current_answer = answer

    raise Exception(
        'Не удалось получить переменные окружения программа остановлена')


if __name__ == '__main__':
    main()
