from phidata.task import Task, TaskArgs
from phidata.utils.log import logger


class DQCheckArgs(TaskArgs):
    pass


class DQCheck(Task):
    """Base Class for all DQChecks"""

    def __init__(self):
        super().__init__()
