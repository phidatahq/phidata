from datetime import datetime
from typing import Optional, Any, Dict

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.utils.context import get_run_date
from phidata.utils.env_var import validate_env_vars
from phidata.utils.log import logger
from phidata.types.context import (
    PathContext,
    RunContext,
    AirflowContext,
    DockerContext,
    K8sContext,
)


class TaskArgs(PhidataBaseArgs):
    # airflow task_id, use name if not provided
    task_id: Optional[str] = None
    # airflow dag_id for this task, set by the workflow
    dag_id: Optional[str] = None

    # run_context provided by workflow
    run_context: Optional[RunContext] = None
    # path_context provided by workflow
    path_context: Optional[PathContext] = None
    # airflow_context provided by workflow
    airflow_context: Optional[AirflowContext] = None

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


class Task(PhidataBase):
    """Base Class for all Tasks"""

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        run_context: Optional[RunContext] = None,
        path_context: Optional[PathContext] = None,
        airflow_context: Optional[AirflowContext] = None,
    ) -> None:
        super().__init__()
        self.args: Optional[TaskArgs] = None
        if name is not None and task_id is not None:
            self.args = TaskArgs(
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                run_context=run_context,
                path_context=path_context,
                airflow_context=airflow_context,
            )

    @property
    def task_id(self) -> str:
        return self.args.task_id if (self.args and self.args.task_id) else self.name

    @task_id.setter
    def task_id(self, task_id: str) -> None:
        if self.args is not None and task_id is not None:
            self.args.task_id = task_id

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
        return self.args.path_context if self.args else None

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

    ######################################################
    ## Build task
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Run task
    ######################################################

    def run_in_local_env(self) -> bool:
        """
        Runs a task in the local environment.

        Returns:
            run_status (bool): True if the run was successful
        """
        logger.debug(f"@run_in_local_env not defined for {self.__class__.__name__}")
        return False

    def run_in_docker_container(
        self,
        active_container: Any,
        docker_env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Runs a task in a docker container.

        Args:
            active_container:
            docker_env:

        Returns:
            run_status (bool): True if the run was successful

        Notes:
            * This function runs in the local environment where phi wf is called from.
            But executes `airflow` commands in the docker container to run the task
        """
        logger.debug(
            f"@run_in_docker_container not defined for {self.__class__.__name__}"
        )
        return False

    def run_in_k8s_container(
        self,
        pod: Any,
        k8s_api_client: Any,
        container_name: Optional[str] = None,
        k8s_env: Optional[Dict[str, str]] = None,
    ) -> bool:
        logger.debug(f"@run_in_k8s_container not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## New Run functions
    ######################################################

    def run_local(
        self,
        env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Runs a task in the local environment.

        Args:
            env:

        Returns:
            run_status (bool): True if the run was successful
        """
        logger.debug(f"@run_local not defined for {self.name}")
        return False

    def run_docker(
        self,
        env: Optional[Dict[str, str]] = None,
        context: Optional[DockerContext] = None,
    ) -> bool:
        """
        Runs a task in a docker container.

        Args:
            env:
            context:

        Returns:
            run_status (bool): True if the run was successful
        """
        logger.debug(f"@run_docker not defined for {self.name}")
        return False

    def run_k8s(
        self,
        env: Optional[Dict[str, str]] = None,
        context: Optional[K8sContext] = None,
    ) -> bool:
        """
        Runs a task in a k8s pod.

        Args:
            env:
            context:

        Returns:
            run_status (bool): True if the run was successful
        """
        logger.debug(f"@run_k8s not defined for {self.name}")
        return False

    ######################################################
    ## Airflow functions
    ######################################################

    def add_airflow_task(
        self, dag: Any, task_group: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Adds the airflow task to the dag and task_group.
        Returns the Operator

        Returns:
            Any subclass of BaseOperator
        """
        logger.debug(f"@add_airflow_task not defined for {self.__class__.__name__}")
        return None
