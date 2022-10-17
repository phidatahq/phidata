from phidata.dq.dq_check import DQCheck, DQCheckArgs


class NonNullCheckArgs(DQCheckArgs):
    pass


class NonNullCheck(DQCheck):
    def __init__(self):
        super().__init__()


class RowsMatchSourceCheckArgs(DQCheckArgs):
    pass


class RowsMatchSourceCheck(DQCheck):
    def __init__(self):
        super().__init__()


class ColumnCheckArgs(DQCheckArgs):
    pass


class ColumnCheck(DQCheck):
    def __init__(self):
        super().__init__()


class InputsValidArgs(DQCheckArgs):
    pass


class InputsValidCheck(DQCheck):
    def __init__(self):
        super().__init__()
