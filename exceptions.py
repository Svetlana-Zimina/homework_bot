class RequestError(Exception):
    """Ошибка при отправке запроса к API."""

    pass


class WrongStatusCodeError(Exception):
    """При отправке запроса к API получен статус отличный от 200."""

    pass


class WrongResponseError(Exception):
    """API вернул неверный json."""

    pass


class UnexpectedStatusError(Exception):
    """Отсутствует или получен неверный статус домашней работы."""

    pass


class WrongKeyError(Exception):
    """В словаре нет ожидаемого ключа."""

    pass
