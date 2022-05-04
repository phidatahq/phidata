from typing import Optional, List
from phidata.workflow.workflow import Workflow


class WorkflowRelatives:
    def __init__(
        self,
        upstream_list: Optional[List[Workflow]] = None,
        downstream_list: Optional[List[Workflow]] = None,
    ):
        # list of workflows that run before i.e. parent workflows
        self.upstream_list: Optional[List[Workflow]] = upstream_list
        # list of workflows that run after i.e. child workflows
        self.downstream_list: Optional[List[Workflow]] = downstream_list

    def add_upstream(self, task: Workflow):
        if self.upstream_list is None:
            self.upstream_list = []
        self.upstream_list.append(task)

    def add_upstream_list(self, tasks: List[Workflow]):
        for task in tasks:
            self.add_upstream(task)

    def add_downstream(self, task: Workflow):
        if self.downstream_list is None:
            self.downstream_list = []
        self.downstream_list.append(task)

    def add_downstream_list(self, tasks: List[Workflow]):
        for task in tasks:
            self.add_downstream(task)
