class AppException(Exception):
    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)
