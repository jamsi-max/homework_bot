class EnvironmentVariablesException(Exception):
    """Исключение проверки переменных окружения."""

    pass


class SendingUserMessageException(Exception):
    """Ошибка отправки сообщения пользователя."""

    pass


class ResponseSerializationException(Exception):
    """Ошибка сериализации ответа от серверая."""

    pass


class EmptyResponseException(Exception):
    """Ответ сервера содержит пустой словарь."""

    pass
