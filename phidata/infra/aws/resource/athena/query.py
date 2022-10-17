from time import sleep
from typing import Optional, Any, Dict, List

from botocore.exceptions import ClientError

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class AthenaQueryExecution(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/athena.html#client
    """

    resource_type = "AthenaQueryExecution"
    service_name = "athena"

    # The SQL query statements to be executed.
    query_string: str
    # A unique case-sensitive string used to ensure the request to create the query
    # is idempotent (executes only once). If another StartQueryExecution request is received,
    # the same response is returned and another query is not created. If a parameter
    # has changed, for example, the QueryString , an error is returned.
    client_request_token: Optional[str] = None
    # The database within which the query executes.
    #     QueryExecutionContext={
    #         'Database': 'string',
    #         'Catalog': 'string'
    #     },
    query_execution_context: Optional[Dict[str, str]] = None
    # Specifies information about where and how to save the results of the query execution.
    # If the query runs in a workgroup, then workgroup's settings may override query settings.
    # This affects the query results location.
    #     ResultConfiguration={
    #         'OutputLocation': 'string',
    #         'EncryptionConfiguration': {
    #             'EncryptionOption': 'SSE_S3'|'SSE_KMS'|'CSE_KMS',
    #             'KmsKey': 'string'
    #         },
    #         'ExpectedBucketOwner': 'string',
    #         'AclConfiguration': {
    #             'S3AclOption': 'BUCKET_OWNER_FULL_CONTROL'
    #         }
    #     },
    result_configuration: Optional[Dict[str, Any]] = None
    work_group: Optional[str] = None

    query_execution_id: Optional[str] = None
    query_execution_state: Optional[str] = None
    wait_for_results: bool = True

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the AthenaQueryExecution

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        # print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            # create a dict of args which are not null, otherwise aws type validation fails
            not_null_args: Dict[str, Any] = {}
            if self.client_request_token:
                not_null_args["ClientRequestToken"] = self.client_request_token
            if self.query_execution_context:
                not_null_args["QueryExecutionContext"] = self.query_execution_context
            if self.result_configuration:
                not_null_args["ResultConfiguration"] = self.result_configuration
            if self.work_group:
                not_null_args["WorkGroup"] = self.work_group

            # Get the service_client
            service_client = self.get_service_client(aws_client)
            print_info(f"Running AthenaQuery: \n\n{self.query_string}\n")
            query_execution_response = service_client.start_query_execution(
                QueryString=self.query_string,
                **not_null_args,
            )
            # logger.debug(f"AthenaQueryExecution: {query_execution_response}")
            # logger.debug(f"AthenaQueryExecution type: {type(query_execution_response)}")

            if query_execution_response is not None:
                self.query_execution_id = query_execution_response.get(
                    "QueryExecutionId", None
                )
                print_info(f"AthenaQueryExecution Id: {self.query_execution_id}")
                self.active_resource = query_execution_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be started.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the AthenaQueryExecution

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_client = self.get_service_client(aws_client)
            if self.query_execution_id is None:
                logger.debug("Athena QueryExecutionId not available")
                return None

            query_execution_response = service_client.get_query_execution(
                QueryExecutionId=self.query_execution_id
            )
            # logger.debug(f"AthenaQueryExecution: {query_execution_response}")
            # logger.debug(f"AthenaQueryExecution type: {type(query_execution_response)}")

            if query_execution_response is not None:
                self.query_execution_id = query_execution_response.get(
                    "QueryExecution", {}
                ).get("QueryExecutionId", None)
                self.query_execution_state = (
                    query_execution_response.get("QueryExecution", {})
                    .get("Status", {})
                    .get("State", None)
                )
                logger.debug(f"AthenaQueryExecution Id: {self.query_execution_id}")
                logger.debug(
                    f"AthenaQueryExecution State: {self.query_execution_state}"
                )
                self.active_resource = query_execution_response
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the AthenaQueryExecution

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
        self.active_resource = None
        print_info(f"AthenaQueryExecution deleted: {self.name}")
        return True

    def get_results(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Streams the results of a single query execution specified by QueryExecutionId
        from the Athena query results location in Amazon S3.

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        logger.debug(
            f"Getting results for {self.get_resource_type()}: {self.get_resource_name()}"
        )
        try:
            if self.query_execution_id is None:
                print_error("Athena QueryExecutionId not available")
                return None

            self._read(aws_client)
            while self.query_execution_state in (
                None,
                "QUEUED",
                "RUNNING",
            ):
                print_info(
                    "Query State: {}".format(
                        self.query_execution_state.lower()
                        if self.query_execution_state
                        else "waiting.."
                    )
                )
                print_info("Sleeping for 5 seconds")
                sleep(5)
                self._read(aws_client)

            # Get the service_client
            service_client = self.get_service_client(aws_client)
            query_results_response = service_client.get_query_results(
                QueryExecutionId=self.query_execution_id,
            )
            # logger.debug(f"query_results_response: {query_results_response}")
            results = query_results_response.get("ResultSet", {}).get("Rows", None)

            return results
        except Exception as e:
            print_warning("AthenaQuery results unavailable. Please try again later.")
            print_warning(e)
        return None
