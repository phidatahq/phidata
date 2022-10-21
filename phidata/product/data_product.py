from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional, Any, List, Dict, Literal

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.asset import DataAsset
from phidata.check import Check
from phidata.exceptions.workflow import WorkflowFailure
from phidata.utils.context import get_run_date, build_path_context_from_env
from phidata.utils.cli_console import print_info, print_subheading
from phidata.utils.log import logger
from phidata.types.run_status import RunStatus
from phidata.types.context import PathContext, RunContext, AirflowContext
from phidata.workflow import Workflow
from phidata.workflow.workflow_relatives import WorkflowRelatives
from phidata.utils.env_var import validate_env_vars


class DataProductArgs(PhidataBaseArgs):
    # List of workflows in this DataProduct
    workflows: Optional[List[Workflow]] = None
    # A dependency graph of the workflows in the format:
    # { downstream: [upstream_list] }
    # The downstream workflow will execute after all workflows in the
    #   upstream_list are finished.
    # upstream_list: workflows which run before the downstream workflow
    # Ex: To run extract -> transform -> load
    #   graph = {
    #     transform: [extract],
    #     load: [transform],
    #     ...
    #   }
    graph: Optional[Dict[Workflow, List[Workflow]]] = None
    # What to do when a workflow fails while running the data_product locally.
    # Continue to next task or stop?
    on_failure: Literal["stop", "continue"] = "stop"

    # Add an EmptyOperator at the start of the workflows
    add_start_task: bool = True
    # Add an EmptyOperator at the end of the workflows
    add_end_task: bool = False

    # airflow dag_id for this data_product, use name if not provided
    dag_id: Optional[str] = None
    # run_context provided by wf_operator
    run_context: Optional[RunContext] = None
    # path_context provided by env variables
    path_context: Optional[PathContext] = None
    # airflow_context provided by airflow
    airflow_context: Optional[AirflowContext] = None
    # Env vars that validate Airflow is active on the containers
    # This is used to gate code blocks which should only run on
    # remote containers like creating DAGs and tasks
    validate_airflow_env: Dict[str, Any] = {"INIT_AIRFLOW": True}

    # Input DataAssets used to build sensors before kicking off the data_product
    inputs: Optional[List[DataAsset]] = None
    # DataAssets produced by this data_product, used for building the lineage graph
    outputs: Optional[List[DataAsset]] = None

    # Checks to run before the data_product
    pre_checks: Optional[List[Check]] = None
    # Checks to run after the data_product
    post_checks: Optional[List[Check]] = None

    @property
    def airflow_active(self) -> bool:
        return validate_env_vars(self.validate_airflow_env)

    @property
    def run_date(self) -> datetime:
        return get_run_date(self.run_context, self.airflow_context)

    @classmethod
    def from_kwargs(cls, kwargs: Optional[Dict] = None):
        if kwargs is None or not isinstance(kwargs, dict):
            return cls()
        # logger.info(f"Loading {cls.__name__} using kwargs")
        args_object = cls(**kwargs)
        validate_airflow_env = kwargs.get("validate_airflow_env", None)
        if validate_env_vars(validate_airflow_env):
            # logger.info("Creating airflow_context")
            airflow_context = AirflowContext(**kwargs)
            args_object.airflow_context = airflow_context
        return args_object


class DataProduct(PhidataBase):
    """Base Class for all DataProducts"""

    def __init__(
        self,
        name: str,
        # List of workflows in this DataProduct,
        workflows: Optional[List[Workflow]] = None,
        # A dependency graph of the workflows in the format:
        # { downstream: [upstream_list] }
        # The downstream workflow will execute after all workflows in the
        #   upstream_list are finished.
        # upstream_list: workflows which run before the downstream workflow
        # Ex: To run extract -> transform -> load
        #   graph = {
        #     transform: [extract],
        #     load: [transform],
        #     ...
        #   }
        graph: Optional[Dict[Workflow, List[Workflow]]] = None,
        # What to do when a task fails while running the workflow locally.
        # Continue to next task or stop?
        on_failure: Literal["stop", "continue"] = "stop",
        # Add an EmptyOperator at the start of the workflows
        add_start_task: bool = True,
        # Add an EmptyOperator at the end of the workflows
        add_end_task: bool = False,
        # airflow dag_id for this workflow, use name if not provided
        dag_id: Optional[str] = None,
        # run_context provided by wf_operator
        run_context: Optional[RunContext] = None,
        # path_context provided by env variables
        path_context: Optional[PathContext] = None,
        # airflow_context provided by airflow
        airflow_context: Optional[AirflowContext] = None,
        # Input DataAssets used to build sensors before kicking off the workflow
        inputs: Optional[List[DataAsset]] = None,
        # DataAssets produced by this workflow, used for building the lineage graph
        outputs: Optional[List[DataAsset]] = None,
        # Checks to run before the workflow
        pre_checks: Optional[List[Check]] = None,
        # Checks to run after the workflow
        post_checks: Optional[List[Check]] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self._family_tree: Optional[Dict[Workflow, WorkflowRelatives]] = None
        try:
            self.args: DataProductArgs = DataProductArgs(
                name=name,
                workflows=workflows,
                graph=graph,
                on_failure=on_failure,
                add_start_task=add_start_task,
                add_end_task=add_end_task,
                dag_id=dag_id,
                run_context=run_context,
                path_context=path_context,
                airflow_context=airflow_context,
                inputs=inputs,
                outputs=outputs,
                pre_checks=pre_checks,
                post_checks=post_checks,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def workflows(self) -> Optional[List[Workflow]]:
        return self.args.workflows if self.args else None

    @workflows.setter
    def workflows(self, workflows: List[Workflow]) -> None:
        if self.args is not None and workflows is not None:
            self.args.workflows = workflows

    @property
    def graph(self) -> Optional[Dict[Workflow, List[Workflow]]]:
        return self.args.graph if self.args else None

    @graph.setter
    def graph(self, graph: Dict[Workflow, List[Workflow]]) -> None:
        if self.args is not None and graph is not None:
            self.args.graph = graph

    @property
    def on_failure(self) -> Literal["stop", "continue"]:
        return self.args.on_failure if self.args else "stop"

    @on_failure.setter
    def on_failure(self, on_failure: Literal["stop", "continue"]) -> None:
        if self.args is not None and on_failure is not None:
            self.args.on_failure = on_failure

    @property
    def add_start_task(self) -> bool:
        return self.args.add_start_task if self.args else False

    @add_start_task.setter
    def add_start_task(self, add_start_task: bool) -> None:
        if self.args is not None and add_start_task is not None:
            self.args.add_start_task = add_start_task

    @property
    def add_end_task(self) -> bool:
        return self.args.add_end_task if self.args else False

    @add_end_task.setter
    def add_end_task(self, add_end_task: bool) -> None:
        if self.args is not None and add_end_task is not None:
            self.args.add_end_task = add_end_task

    @property
    def dag_id(self) -> str:
        return self.args.dag_id if (self.args and self.args.dag_id) else self.name

    @dag_id.setter
    def dag_id(self, dag_id: str) -> None:
        if self.args is not None and dag_id is not None:
            self.args.dag_id = dag_id

    @property
    def run_context(self) -> Optional[RunContext]:
        return self.args.run_context if self.args else None

    @run_context.setter
    def run_context(self, run_context: RunContext) -> None:
        if self.args is not None and run_context is not None:
            self.args.run_context = run_context

    @property
    def path_context(self) -> Optional[PathContext]:
        # Workflow not yet initialized
        if self.args is None:
            return None

        if self.args.path_context is not None:
            # use cached value if available
            return self.args.path_context

        self.args.path_context = build_path_context_from_env()
        return self.args.path_context

    @path_context.setter
    def path_context(self, path_context: PathContext) -> None:
        if self.args is not None and path_context is not None:
            self.args.path_context = path_context

    @property
    def airflow_context(self) -> Optional[AirflowContext]:
        return self.args.airflow_context if self.args else None

    @airflow_context.setter
    def airflow_context(self, airflow_context: AirflowContext) -> None:
        if self.args is not None and airflow_context is not None:
            self.args.airflow_context = airflow_context

    @property
    def inputs(self) -> Optional[List[DataAsset]]:
        return self.args.inputs if self.args else None

    @inputs.setter
    def inputs(self, inputs: List[DataAsset]) -> None:
        if self.args is not None and inputs is not None:
            self.args.inputs = inputs

    @property
    def outputs(self) -> Optional[List[DataAsset]]:
        return self.args.outputs if self.args else None

    @outputs.setter
    def outputs(self, outputs: List[DataAsset]) -> None:
        if self.args is not None and outputs is not None:
            self.args.outputs = outputs

    @property
    def pre_checks(self) -> Optional[List[Check]]:
        return self.args.pre_checks if self.args else None

    @pre_checks.setter
    def pre_checks(self, pre_checks: List[Check]) -> None:
        if self.args is not None and pre_checks is not None:
            self.args.pre_checks = pre_checks

    @property
    def post_checks(self) -> Optional[List[Check]]:
        return self.args.post_checks if self.args else None

    @post_checks.setter
    def post_checks(self, post_checks: List[Check]) -> None:
        if self.args is not None and post_checks is not None:
            self.args.post_checks = post_checks

    ######################################################
    ## DataProduct Properties
    ######################################################

    @property
    def airflow_active(self) -> bool:
        return validate_env_vars(self.args.validate_airflow_env)

    @property
    def family_tree(self) -> Optional[Dict[Workflow, WorkflowRelatives]]:
        if self.workflows is None:
            return None

        # used cached value if available
        if self._family_tree is not None:
            return self._family_tree

        # build family_tree
        family_tree: Dict[Workflow, WorkflowRelatives] = OrderedDict()
        for workflow in self.workflows:
            family_tree[workflow] = WorkflowRelatives()

        if self.graph is None:
            return family_tree

        for workflow, upstream_list in self.graph.items():
            family_tree[workflow].add_upstream_list(upstream_list)
            for upstream_workflow in upstream_list:
                family_tree[upstream_workflow].add_downstream(workflow)

        return family_tree

    @property
    def family_tree_dict(self) -> Dict[str, Dict[str, List[str]]]:
        tree: Dict[str, Dict[str, List[str]]] = OrderedDict()
        family_tree = self.family_tree
        if family_tree is None:
            return tree

        for workflow in family_tree:
            workflow_tree = {}
            upstream_list = family_tree[workflow].upstream_list
            downstream_list = family_tree[workflow].downstream_list
            if upstream_list:
                workflow_tree["upstream"] = [wf.name for wf in upstream_list]
            if downstream_list:
                workflow_tree["downstream"] = [wf.name for wf in downstream_list]
            tree[workflow.name] = workflow_tree
        return tree

    @property
    def roots(self) -> Optional[List[Workflow]]:
        """
        Roots are workflows that run first. i.e. have nothing upstream of them
        """
        if self.graph is None:
            return self.workflows

        family_tree: Optional[Dict[Workflow, WorkflowRelatives]] = self.family_tree
        if family_tree is None:
            return self.workflows

        roots: List[Workflow] = []
        for workflow, relatives in family_tree.items():
            if relatives.upstream_list is None:
                roots.append(workflow)
        return roots

    @property
    def leaves(self) -> Optional[List[Workflow]]:
        """
        Leaves are workflows that run last. i.e. have nothing downstream of them
        """
        if self.graph is None:
            return self.workflows

        family_tree: Optional[Dict[Workflow, WorkflowRelatives]] = self.family_tree
        if family_tree is None:
            return self.workflows

        leaves: List[Workflow] = []
        for workflow, relatives in family_tree.items():
            if relatives.downstream_list is None:
                leaves.append(workflow)
        return leaves

    def __call__(self, *args, **kwargs) -> bool:
        logger.warning("DataProducts should not be called directly")
        return True

    ######################################################
    ## Build data_product
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Workflows
    ######################################################

    def add_workflow(self, workflow: Workflow):
        if self.args.workflows is None:
            self.args.workflows = []
        self.args.workflows.append(workflow)

    ######################################################
    ## Checks
    ######################################################

    def add_pre_check(self, check: Check):
        if self.args.pre_checks is None:
            self.args.pre_checks = []
        self.args.pre_checks.append(check)

    def add_post_check(self, check: Check):
        if self.args.post_checks is None:
            self.args.post_checks = []
        self.args.post_checks.append(check)

    ######################################################
    ## Run data_product
    ######################################################

    def run_workflow_in_local_env(
        self, workflow: Workflow, task_id: Optional[str] = None
    ) -> RunStatus:
        wf_name = workflow.name
        print_subheading(f"\nRunning workflow: {wf_name}")
        # Pass down context
        workflow.run_context = self.run_context
        workflow.path_context = self.path_context
        workflow.airflow_context = self.airflow_context
        # Not required for local runs but adding for posterity
        if self.dag_id:
            workflow.dag_id = self.dag_id
        run_success = workflow.run_in_local_env(task_id=task_id)
        return RunStatus(name=wf_name, success=run_success)

    def run_in_local_env(
        self, workflow_name: Optional[str] = None, task_id: Optional[str] = None
    ) -> bool:
        """
        Runs a DataProduct in the local environment where phi wf is called from.

        Returns:
            run_status (bool): True if the run was successful
        """
        from phidata.utils.cli_console import print_run_status_table

        logger.info("--**-- Running DataProduct locally")

        if self.workflows is None:
            logger.info("No workflows to run")
            return True

        wf_run_status: List[RunStatus] = []
        if workflow_name is not None:
            wf_name_map = {wf.name: wf for wf in self.workflows}
            if workflow_name in wf_name_map:
                wf_run_status.append(
                    self.run_workflow_in_local_env(
                        workflow=wf_name_map[workflow_name], task_id=task_id
                    )
                )
            else:
                logger.error(f"Could not find {workflow_name} in {wf_name_map.keys()}")
        else:
            for wf in self.workflows:
                run_status = self.run_workflow_in_local_env(wf)
                wf_run_status.append(run_status)
                if not run_status.success and self.args.on_failure == "stop":
                    # logger.error(f"Workflow {wf.name} failed")
                    break

        print_run_status_table("Workflow Run Status", wf_run_status)
        for run_status in wf_run_status:
            if not run_status.success:
                return False
        return True

    def run_workflow_in_docker_container(
        self,
        workflow: Workflow,
        active_container: Any,
        docker_env: Optional[Dict[str, str]] = None,
        task_id: Optional[str] = None,
    ) -> RunStatus:
        _wf_name = workflow.name
        print_subheading(f"\nRunning workflow: {_wf_name}")
        # Pass down context
        workflow.run_context = self.run_context
        workflow.path_context = self.path_context
        workflow.airflow_context = self.airflow_context
        workflow.dag_id = self.dag_id
        run_success = workflow.run_in_docker_container(
            active_container=active_container, docker_env=docker_env, task_id=task_id
        )
        return RunStatus(name=_wf_name, success=run_success)

    def run_in_docker_container(
        self,
        active_container: Any,
        docker_env: Optional[Dict[str, str]] = None,
        workflow_name: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> bool:
        """
        Runs a DataProduct in a docker container.

        Args:
            active_container:
            docker_env:
            workflow_name:
            task_id:

        Returns:
            run_status (bool): True if the run was successful

        Notes:
            * This function runs in the local environment where phi wf is called from.
            But executes `airflow` commands in the docker container to run the workflow
            * For the airflow tasks to be available, they need to be added to the DAG
            using add_airflow_tasks_to_dag()
        """
        from phidata.utils.cli_console import print_run_status_table

        logger.info("--**-- Running DataProduct in docker container")

        if self.workflows is None:
            logger.info("No workflows to run")
            return True

        wf_run_status: List[RunStatus] = []
        if workflow_name is not None:
            wf_name_map = {wf.name: wf for wf in self.workflows}
            if workflow_name in wf_name_map:
                wf_run_status.append(
                    self.run_workflow_in_docker_container(
                        workflow=wf_name_map[workflow_name],
                        active_container=active_container,
                        docker_env=docker_env,
                        task_id=task_id,
                    )
                )
            else:
                logger.error(f"Could not find {workflow_name} in {wf_name_map.keys()}")
        else:
            for wf in self.workflows:
                run_status = self.run_workflow_in_docker_container(
                    workflow=wf,
                    active_container=active_container,
                    docker_env=docker_env,
                )
                wf_run_status.append(run_status)
                if not run_status.success and self.args.on_failure == "stop":
                    raise WorkflowFailure(f"Workflow {wf.name} failed")

        print_run_status_table("Workflow Run Status", wf_run_status)
        for run_status in wf_run_status:
            if not run_status.success:
                return False
        return True

    def run_in_k8s_container(
        self,
        pod: Any,
        k8s_api_client: Any,
        container_name: Optional[str] = None,
        k8s_env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Runs a DataProduct in a k8s container.

        Args:
            pod: The pod to run the workflow in
            k8s_api_client: K8sApiClient
            container_name: The container to run the workflow in
            k8s_env:

        Returns:
            run_status (bool): True if the run was successful

        Notes:
            * This function runs in the local environment where phi wf is called from.
            But executes `airflow` commands in the k8s container to run the workflow
            * For the airflow tasks to be available, they need to be added to the DAG
            using add_airflow_tasks_to_dag()
        """
        logger.info("--**-- Running DataProduct in k8s container")

        if self.workflows is None:
            logger.info("No workflows to run")
            return True

        wf_run_status: List[RunStatus] = []
        for idx, wf in enumerate(self.workflows, start=1):
            wf_name = wf.name or "{}__{}".format(wf.__class__.__name__, idx)
            print_subheading(f"\nRunning {wf_name}")
            # Pass down context
            wf.run_context = self.run_context
            wf.path_context = self.path_context
            wf.airflow_context = self.airflow_context
            wf.dag_id = self.dag_id
            run_success = wf.run_in_k8s_container(
                pod=pod,
                k8s_api_client=k8s_api_client,
                container_name=container_name,
                k8s_env=k8s_env,
            )
            wf_run_status.append(RunStatus(name=wf_name, success=run_success))

        print_subheading("\nWorkflow run status:")
        print_info(
            "\n".join(
                [
                    "{}: {}".format(wf.name, "Success" if wf.success else "Fail")
                    for wf in wf_run_status
                ]
            )
        )
        print_info("")
        for _run in wf_run_status:
            if not _run.success:
                return False
        return True

    ######################################################
    ## Airflow functions
    ######################################################

    def create_airflow_dag(
        self,
        owner: Optional[str] = "airflow",
        depends_on_past: Optional[bool] = False,
        # The description for the DAG to e.g. be shown on the webserver
        description: Optional[str] = None,
        # Defines how often that DAG runs, this
        #  timedelta object gets added to your latest task instance's
        #  execution_date to figure out the next schedule
        # Default: daily
        schedule_interval: timedelta = timedelta(days=1),
        # The timestamp from which the scheduler will
        #  attempt to backfill
        start_date: Optional[datetime] = None,
        # if start_date is not provided, use start_days_ago
        start_days_ago: int = 1,
        # A date beyond which your DAG won't run, leave to None
        #  for open ended scheduling
        end_date: Optional[datetime] = None,
        # a dictionary of macros that will be exposed
        #  in your jinja templates. For example, passing ``dict(foo='bar')``
        #  to this argument allows you to ``{{ foo }}`` in all jinja
        #  templates related to this DAG. Note that you can pass any
        #  type of object here.
        user_defined_macros: Optional[Dict] = None,
        # a dictionary of filters that will be exposed
        #  in your jinja templates. For example, passing
        #  ``dict(hello=lambda name: 'Hello %s' % name)`` to this argument allows
        #  you to ``{{ 'world' | hello }}`` in all jinja templates related to
        #  this DAG.
        user_defined_filters: Optional[Dict] = None,
        # A dictionary of default parameters to be used
        #  as constructor keyword parameters when initialising operators.
        #  Note that operators have the same hook, and precede those defined
        #  here, meaning that if your dict contains `'depends_on_past': True`
        #  here and `'depends_on_past': False` in the operator's call
        #  `default_args`, the actual value will be `False`.
        default_args: Optional[Dict] = None,
        # the number of task instances allowed to run concurrently
        concurrency: Optional[int] = None,
        # maximum number of active DAG runs, beyond this
        #  number of DAG runs in a running state, the scheduler won't create
        #  new active DAG runs
        max_active_runs: int = 8,
        doc_md: Optional[str] = None,
        # a dictionary of DAG level parameters that are made
        # accessible in templates, namespaced under `params`. These
        # params can be overridden at the task level.
        params: Optional[Dict] = None,
        is_paused_upon_creation: Optional[bool] = None,
        jinja_environment_kwargs: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Any:
        """
        Used to create an Airflow DAG for the DataProduct.
        """

        # Skips DAG creation on local machines
        if not self.airflow_active:
            return None

        from airflow import DAG
        from airflow.models.operator import Operator
        from airflow.utils.dates import days_ago

        operator_default_args = default_args
        if operator_default_args is None:
            operator_default_args = {}
        operator_default_args.update(
            {
                "owner": owner,
                "depends_on_past": depends_on_past,
            }
        )
        if start_date is None:
            start_date = days_ago(start_days_ago)

        dag_id = self.dag_id
        if dag_id is None:
            logger.error("DataProduct dag_id unavailable")
            return None
        if self.workflows is None:
            logger.error(f"DataProduct has no workflows")
            return None
        dag = DAG(
            dag_id=dag_id,
            description=description,
            schedule_interval=schedule_interval,
            start_date=start_date,
            end_date=end_date,
            user_defined_macros=user_defined_macros,
            user_defined_filters=user_defined_filters,
            default_args=operator_default_args,
            concurrency=concurrency,
            max_active_runs=max_active_runs,
            doc_md=doc_md,
            params=params,
            is_paused_upon_creation=is_paused_upon_creation,
            jinja_environment_kwargs=jinja_environment_kwargs,
            tags=tags,
        )

        # Add airflow tasks from workflows to DAG
        for workflow in self.workflows:
            # Add start tasks to workflows if there are inter-workflow dependencies
            if self.add_start_task or self.graph is not None:
                workflow.add_start_task = True
            if self.add_end_task or self.graph is not None:
                workflow.add_end_task = True
            # logger.info(f"Adding tasks for workflow: {workflow.name}")
            add_task_success = workflow.add_airflow_tasks_to_dag(dag=dag)
            if not add_task_success:
                logger.error(f"Tasks for workflow {workflow.name} could not be added")

        if self.graph is not None:
            # logger.info("Updating dependencies")
            for downstream_workflow, upstream_workflow_list in self.graph.items():

                downstream_wf_start_task: Optional[Operator] = None
                downstream_wf_start_task_id = downstream_workflow.start_workflow_task_id
                # logger.info(f"downstream_workflow_start: {downstream_wf_start_task_id}")
                if dag.has_task(downstream_wf_start_task_id):
                    downstream_wf_start_task = dag.get_task(downstream_wf_start_task_id)
                if downstream_wf_start_task is None:
                    logger.info(f"Cannot find task: {downstream_wf_start_task_id}")
                    continue

                for workflow in upstream_workflow_list:
                    upstream_wf_end_task: Optional[Operator] = None
                    upstream_wf_end_task_id = workflow.end_workflow_task_id
                    # logger.info(f"upstream_workflow_end: {upstream_wf_end_task_id}")

                    if dag.has_task(upstream_wf_end_task_id):
                        upstream_wf_end_task = dag.get_task(upstream_wf_end_task_id)

                    if upstream_wf_end_task is not None:
                        downstream_wf_start_task.set_upstream(upstream_wf_end_task)

                # logger.info(f"Upstream: {downstream_wf_start_task.upstream_task_ids}")
        logger.debug(f"Airflow dag {dag_id} created")
        return dag
