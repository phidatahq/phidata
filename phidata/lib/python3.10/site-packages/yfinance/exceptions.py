class YFinanceException(Exception):
    pass


class YFinanceDataException(YFinanceException):
    pass


class YFNotImplementedError(NotImplementedError):
    def __init__(self, method_name):
        super().__init__(f"Have not implemented fetching '{method_name}' from Yahoo API")

