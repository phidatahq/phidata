from phidata.task import Task, TaskArgs
from phidata.utils.log import logger


class CheckArgs(TaskArgs):
    pass


class Check(Task):
    """Base Class for all DQChecks"""

    def __init__(self):
        super().__init__()
