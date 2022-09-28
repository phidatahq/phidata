from typing import Optional, List, Dict, Any

from phidata.asset.aws import AwsAsset, AwsAssetArgs
from phidata.infra.aws.resource.athena.query import AthenaQueryExecution
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class AthenaQueryArgs(AwsAssetArgs):
    # The SQL query statements to be executed.
    query_string: str
    # A unique case-sensitive string used to ensure the request to create the query
    # is idempotent (executes only once). If another StartQueryExecution request is received,
    # the same response is returned and another query is not created. If a parameter
    # has changed, for example, the QueryString , an error is returned.
    client_request_token: Optional[str] = None
    # QueryExecutionContext
    # The database within which the query executes.
    # The database must exist in the catalog.
    database: Optional[str] = None
    # The name of the data catalog used in the query execution.
    catalog: Optional[str] = None

    # ResultConfiguration
    # Specifies information about where and how to save the results of the query execution.
    # The location in Amazon S3 where your query results are stored,
    # such as s3://path/to/query/bucket/ . To run the query, you must specify the query
    # results location using one of the ways: either for individual queries using either
    # this setting (client-side), or in the workgroup, using WorkGroupConfiguration .
    # If none of them is set, Athena issues an error that no output location is provided.
    output_location: Optional[str] = None
    work_group: Optional[str] = None

    query_execution_id: Optional[str] = None
    wait_for_results: bool = True

    ## Resource management
    # If True, skip resource creation if active resources with the same name exist.
    use_cache: bool = True
    # If True, logs extra debug messages
    use_verbose_logs: bool = True


class AthenaQuery(AwsAsset):
    def __init__(
        self,
        # Name for this query.
        name: str,
        # The SQL query statements to be executed.
        query_string: str,
        # A unique case-sensitive string used to ensure the request to create the query
        # is idempotent (executes only once). If another StartQueryExecution request is received,
        # the same response is returned and another query is not created. If a parameter
        # has changed, for example, the QueryString , an error is returned.
        client_request_token: Optional[str] = None,
        # QueryExecutionContext
        # The database within which the query executes.
        # The database must exist in the catalog.
        database: Optional[str] = None,
        # The name of the data catalog used in the query execution.
        catalog: Optional[str] = None,
        # ResultConfiguration
        # Specifies information about where and how to save the results of the query execution.
        # The location in Amazon S3 where your query results are stored,
        # such as s3://path/to/query/bucket/ . To run the query, you must specify the query
        # results location using one of the ways: either for individual queries using either
        # this setting (client-side), or in the workgroup, using WorkGroupConfiguration .
        # If none of them is set, Athena issues an error that no output location is provided.
        output_location: Optional[str] = None,
        work_group: Optional[str] = None,
        query_execution_id: Optional[str] = None,
        wait_for_results: bool = True,
        ## Resource management
        # If True, skip resource creation if active resources with the same name exist.
        use_cache: bool = True,
        # If True, logs extra debug messages
        use_verbose_logs: bool = True,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:

        super().__init__()
        try:
            self.args: AthenaQueryArgs = AthenaQueryArgs(
                name=name,
                query_string=query_string,
                client_request_token=client_request_token,
                database=database,
                catalog=catalog,
                output_location=output_location,
                work_group=work_group,
                query_execution_id=query_execution_id,
                wait_for_results=wait_for_results,
                use_cache=use_cache,
                use_verbose_logs=use_verbose_logs,
                version=version,
                enabled=enabled,
            )
            self._athena_query_execution: Optional[AthenaQueryExecution] = None
        except Exception as e:
            print_error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def athena_query_execution(self) -> AthenaQueryExecution:
        # use cached value if available
        if self._athena_query_execution:
            return self._athena_query_execution

        # Create AthenaQueryExecution object
        logger.debug("Init AthenaQueryExecution")
        try:
            query_execution_context = None
            if self.args.database or self.args.catalog:
                query_execution_context = {}
                if self.args.database:
                    query_execution_context["Database"] = self.args.database
                if self.args.catalog:
                    query_execution_context["Catalog"] = self.args.catalog

            result_configuration = None
            if self.args.output_location:
                result_configuration = {
                    "OutputLocation": self.args.output_location,
                }

            self._athena_query_execution = AthenaQueryExecution(
                name=self.name,
                query_string=self.args.query_string,
                client_request_token=self.args.client_request_token,
                query_execution_context=query_execution_context,
                result_configuration=result_configuration,
                work_group=self.args.work_group,
                query_execution_id=self.args.query_execution_id,
                use_cache=self.args.use_cache,
            )
            return self._athena_query_execution
        except Exception as e:
            print_error(f"Could not create AthenaQueryExecution")
            raise

    ######################################################
    ## Start AthenaQuery
    ######################################################

    def start_query(self) -> bool:

        # AthenaQuery not yet initialized
        if self.args is None:
            return False

        from phidata.infra.aws.api_client import AwsApiClient

        try:
            # aws_region, aws_profile loaded from local env if provided
            # by WorkspaceConfig
            aws_api_client = AwsApiClient(
                aws_region=self.aws_region,
                aws_profile=self.aws_profile,
            )
            athena_query_execution = self.athena_query_execution
            # logger.debug(f"Running: {self._athena_query_execution.dict()}")
            create_success = athena_query_execution.create(aws_api_client)
            return create_success
        except Exception as e:
            print_error("Could not start AthenaQuery, please try again")
            logger.exception(e)
        return False

    ######################################################
    ## Get results for AthenaQuery
    ######################################################

    def get_results(self) -> Any:

        # AthenaQuery not yet initialized
        if self.args is None:
            return False

        from phidata.infra.aws.api_client import AwsApiClient

        aws_api_client = AwsApiClient(
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
        )
        athena_query_execution = self.athena_query_execution
        active_athena_query_execution = athena_query_execution.read(aws_api_client)
        if active_athena_query_execution is None:
            print_error("No AthenaQuery available")
            return False

        results = athena_query_execution.get_results(aws_api_client)
        return results
