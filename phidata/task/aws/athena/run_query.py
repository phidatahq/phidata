from typing import Optional

from phidata.asset.aws.athena.query import AthenaQuery
from phidata.utils.cli_console import print_info, print_heading
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class RunAthenaQueryArgs(PythonTaskArgs):
    query: AthenaQuery
    get_results: bool = False


class RunAthenaQuery(PythonTask):
    def __init__(
        self,
        query: AthenaQuery,
        get_results: bool = False,
        name: str = "run_athena_query",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: RunAthenaQueryArgs = RunAthenaQueryArgs(
                query=query,
                get_results=get_results,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=run_athena_query,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def query(self) -> AthenaQuery:
        return self.args.query

    @query.setter
    def query(self, query: AthenaQuery) -> None:
        if query is not None:
            self.args.query = query

    @property
    def get_results(self) -> bool:
        return self.args.get_results

    @get_results.setter
    def get_results(self, get_results: bool) -> None:
        if get_results is not None:
            self.args.get_results = get_results


def run_athena_query(**kwargs) -> bool:

    args: RunAthenaQueryArgs = RunAthenaQueryArgs(**kwargs)
    # logger.debug("RunAthenaQueryArgs: {}".format(args))

    start_success = args.query.start_query()
    if start_success:
        logger.info("AthenaQuery started")
        if args.get_results:
            logger.info(f"Getting results")
            results = args.query.get_results()
            if results:
                print_heading("\nAthenaQuery result")
                print_info(results)
            return start_success
    return start_success
