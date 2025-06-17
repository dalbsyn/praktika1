class CardError(Exception):
    """
    Пользовательское исключение для передачи кодов ошибок Epay
    """
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message