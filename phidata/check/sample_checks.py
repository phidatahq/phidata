from phidata.check.check import Check, CheckArgs


class NonNullCheckArgs(CheckArgs):
    pass


class NonNullCheck(Check):
    def __init__(self):
        super().__init__()


class RowsMatchSourceCheckArgs(CheckArgs):
    pass


class RowsMatchSourceCheck(Check):
    def __init__(self):
        super().__init__()


class ColumnCheckArgs(CheckArgs):
    pass


class ColumnCheck(Check):
    def __init__(self):
        super().__init__()


class InputsValidArgs(CheckArgs):
    pass


class InputsValidCheck(Check):
    def __init__(self):
        super().__init__()
