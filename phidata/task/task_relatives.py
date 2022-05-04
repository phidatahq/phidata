from typing import Optional, List
from phidata.task.task import Task


class TaskRelatives:
    def __init__(
        self,
        upstream_list: Optional[List[Task]] = None,
        downstream_list: Optional[List[Task]] = None,
    ):
        # list of tasks that run before i.e. parent tasks
        self.upstream_list: Optional[List[Task]] = upstream_list
        # list of tasks that run after i.e. child tasks
        self.downstream_list: Optional[List[Task]] = downstream_list

    def add_upstream(self, task: Task):
        if self.upstream_list is None:
            self.upstream_list = []
        self.upstream_list.append(task)

    def add_upstream_list(self, tasks: List[Task]):
        for task in tasks:
            self.add_upstream(task)

    def add_downstream(self, task: Task):
        if self.downstream_list is None:
            self.downstream_list = []
        self.downstream_list.append(task)

    def add_downstream_list(self, tasks: List[Task]):
        for task in tasks:
            self.add_downstream(task)
