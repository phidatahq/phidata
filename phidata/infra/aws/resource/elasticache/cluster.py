from pathlib import Path
from typing import Optional, Any, Dict, List, Literal

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.infra.aws.resource.rds.db_instance import DbInstance
from phidata.infra.aws.resource.rds.db_subnet_group import DbSubnetGroup
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class CacheCluster(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html
    """

    resource_type = "CacheCluster"
    service_name = "elasticache"

    # Name of the cluster.
    name: str
    # The node group (shard) identifier. This parameter is stored as a lowercase string.
    # If None, use the name as the cache_cluster_id
    # Constraints:
    #   A name must contain from 1 to 50 alphanumeric characters or hyphens.
    #   The first character must be a letter.
    #   A name cannot end with a hyphen or contain two consecutive hyphens.
    cache_cluster_id: Optional[str] = None
    # The ID of the replication group to which this cluster should belong.
    # If this parameter is specified, the cluster is added to the specified replication group as a read replica;
    # otherwise, the cluster is a standalone primary that is not part of any replication group.
    replication_group_id: Optional[str] = None
    # Specifies whether the nodes in this Memcached cluster are created in a single Availability Zone or created across multiple Availability Zones in the cluster's region.
    # This parameter is only supported for Memcached clusters.
    az_mode: Optional[Literal["single-az", "cross-az"]] = None
    # The EC2 Availability Zone in which the cluster is created.
    # All nodes belonging to this cluster are placed in the preferred Availability Zone. If you want to create your nodes across multiple Availability Zones, use PreferredAvailabilityZones .
    # Default: System chosen Availability Zone.
    preferred_availability_zone: Optional[str] = None
    # A list of the Availability Zones in which cache nodes are created. The order of the zones in the list is not important.
    # This option is only supported on Memcached.
    preferred_availability_zones: Optional[List[str]] = None
    # The initial number of cache nodes that the cluster has.
    # For clusters running Redis, this value must be 1. For clusters running Memcached, this value must be between 1 and 40.
    num_cache_nodes: Optional[int] = None
    # Compute and memory capacity of the nodes in the node group (shard).
    cache_node_type: Optional[str] = None
    # The name of the cache engine to be used for this cluster.
    # Valid values for this parameter are: memcached | redis
    engine: Optional[Literal["memcached", "redis"]] = None
    # The version number of the cache engine to be used for this cluster.
    engine_version: Optional[str] = None
    cache_parameter_group_name: Optional[str] = None
    cache_subnet_group_name: Optional[str] = None
    cache_security_group_names: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None
    tags: Optional[List[Dict[str, str]]] = None
    snapshot_arns: Optional[List[str]] = None
    snapshot_name: Optional[str] = None
    preferred_maintenance_window: Optional[str] = None
    # The version number of the cache engine to be used for this cluster.
    port: Optional[int] = None
    notification_topic_arn: Optional[str] = None
    auto_minor_version_upgrade: Optional[bool] = None
    snapshot_retention_limit: Optional[int] = None
    snapshot_window: Optional[str] = None
    # The password used to access a password protected server.
    # Password constraints:
    # - Must be only printable ASCII characters.
    # - Must be at least 16 characters and no more than 128 characters in length.
    # - The only permitted printable special characters are !, &, #, $, ^, <, >, and -.
    # Other printable special characters cannot be used in the AUTH token.
    # - For more information, see AUTH password at http://redis.io/commands/AUTH.
    auth_token: Optional[str] = None
    outpost_mode: Optional[Literal["single-outpost", "cross-outpost"]] = None
    preferred_outpost_arn: Optional[str] = None
    preferred_outpost_arns: Optional[List[str]] = None
    log_delivery_configurations: Optional[List[Dict[str, Any]]] = None
    transit_encryption_enabled: Optional[bool] = None
    network_type: Optional[Literal["ipv4", "ipv6", "dual_stack"]] = None
    ip_discovery: Optional[Literal["ipv4", "ipv6"]] = None

    # Cache secret_data
    cached_secret_data: Optional[Dict[str, Any]] = None

    def get_cache_cluster_id(self):
        return self.cache_cluster_id or self.name

    def get_secret_data(self) -> Optional[Dict[str, str]]:
        if self.cached_secret_data is not None:
            return self.cached_secret_data

        if self.secrets_file is not None:
            self.cached_secret_data = self.read_yaml_file(self.secrets_file)
        return self.cached_secret_data

    def get_master_username(self) -> Optional[str]:
        master_username = self.master_username
        if master_username is None and self.secrets_file is not None:
            # read from secrets_file
            secret_data = self.get_secret_data()
            if secret_data is not None:
                master_username = secret_data.get("MASTER_USERNAME", master_username)
        return master_username

    def get_master_user_password(self) -> Optional[str]:
        master_user_password = self.master_user_password
        if master_user_password is None and self.secrets_file is not None:
            # read from secrets_file
            secret_data = self.get_secret_data()
            if secret_data is not None:
                master_user_password = secret_data.get(
                    "MASTER_USER_PASSWORD", master_user_password
                )
        return master_user_password

    def get_database_name(self) -> Optional[str]:
        database_name = self.database_name
        if database_name is None and self.secrets_file is not None:
            # read from secrets_file
            secret_data = self.get_secret_data()
            if secret_data is not None:
                database_name = secret_data.get("DATABASE_NAME", database_name)
        return database_name

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the CacheCluster

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Get the VpcSecurityGroupIds
        vpc_security_group_ids = self.vpc_security_group_ids
        if vpc_security_group_ids is None and self.vpc_stack is not None:
            vpc_stack_sg = self.vpc_stack.get_security_group(aws_client=aws_client)
            if vpc_stack_sg is not None:
                logger.debug(f"Using SecurityGroup: {vpc_stack_sg}")
                vpc_security_group_ids = [vpc_stack_sg]

        # Step 2: Get the DbSubnetGroupName
        db_subnet_group_name = self.db_subnet_group_name
        if db_subnet_group_name is None and self.db_subnet_group is not None:
            db_subnet_group_name = self.db_subnet_group.name
            logger.debug(f"Using DbSubnetGroup: {db_subnet_group_name}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.availability_zones:
            not_null_args["AvailabilityZones"] = self.availability_zones
        if self.backup_retention_period:
            not_null_args["BackupRetentionPeriod"] = self.backup_retention_period
        if self.character_set_name:
            not_null_args["CharacterSetName"] = self.character_set_name

        database_name = self.get_database_name()
        if database_name:
            not_null_args["DatabaseName"] = database_name

        if self.db_cluster_parameter_group_name:
            not_null_args[
                "DBClusterParameterGroupName"
            ] = self.db_cluster_parameter_group_name

        if vpc_security_group_ids is not None:
            not_null_args["VpcSecurityGroupIds"] = vpc_security_group_ids
        if db_subnet_group_name is not None:
            not_null_args["DBSubnetGroupName"] = db_subnet_group_name

        if self.engine_version:
            not_null_args["EngineVersion"] = self.engine_version
        if self.port:
            not_null_args["Port"] = self.port

        master_username = self.get_master_username()
        if master_username:
            not_null_args["MasterUsername"] = master_username
        master_user_password = self.get_master_user_password()
        if master_user_password:
            not_null_args["MasterUserPassword"] = master_user_password

        if self.option_group_name:
            not_null_args["OptionGroupName"] = self.option_group_name
        if self.preferred_backup_window:
            not_null_args["PreferredBackupWindow"] = self.preferred_backup_window
        if self.preferred_maintenance_window:
            not_null_args[
                "PreferredMaintenanceWindow"
            ] = self.preferred_maintenance_window
        if self.replication_source_identifier:
            not_null_args[
                "ReplicationSourceIdentifier"
            ] = self.replication_source_identifier
        if self.tags:
            not_null_args["Tags"] = self.tags
        if self.storage_encrypted:
            not_null_args["StorageEncrypted"] = self.storage_encrypted
        if self.kms_key_id:
            not_null_args["KmsKeyId"] = self.kms_key_id
        if self.enable_iam_database_authentication:
            not_null_args[
                "EnableIAMCacheClusterAuthentication"
            ] = self.enable_iam_database_authentication
        if self.backtrack_window:
            not_null_args["BacktrackWindow"] = self.backtrack_window
        if self.enable_cloudwatch_logs_exports:
            not_null_args[
                "EnableCloudwatchLogsExports"
            ] = self.enable_cloudwatch_logs_exports
        if self.engine_mode:
            not_null_args["EngineMode"] = self.engine_mode
        if self.scaling_configuration:
            not_null_args["ScalingConfiguration"] = self.scaling_configuration
        if self.deletion_protection:
            not_null_args["DeletionProtection"] = self.deletion_protection
        if self.global_cluster_identifier:
            not_null_args["GlobalClusterIdentifier"] = self.global_cluster_identifier
        if self.enable_http_endpoint:
            not_null_args["EnableHttpEndpoint"] = self.enable_http_endpoint
        if self.copy_tags_to_snapshot:
            not_null_args["CopyTagsToSnapshot"] = self.copy_tags_to_snapshot
        if self.domain:
            not_null_args["Domain"] = self.domain
        if self.domain_iam_role_name:
            not_null_args["DomainIAMRoleName"] = self.domain_iam_role_name
        if self.enable_global_write_forwarding:
            not_null_args[
                "EnableGlobalWriteForwarding"
            ] = self.enable_global_write_forwarding
        if self.db_instance_class:
            not_null_args["DBClusterInstanceClass"] = self.db_instance_class
        if self.allocated_storage:
            not_null_args["AllocatedStorage"] = self.allocated_storage
        if self.storage_type:
            not_null_args["StorageType"] = self.storage_type
        if self.iops:
            not_null_args["Iops"] = self.iops
        if self.publicly_accessible:
            not_null_args["PubliclyAccessible"] = self.publicly_accessible
        if self.auto_minor_version_upgrade:
            not_null_args["AutoMinorVersionUpgrade"] = self.auto_minor_version_upgrade
        if self.monitoring_interval:
            not_null_args["MonitoringInterval"] = self.monitoring_interval
        if self.monitoring_role_arn:
            not_null_args["MonitoringRoleArn"] = self.monitoring_role_arn
        if self.enable_performance_insights:
            not_null_args[
                "EnablePerformanceInsights"
            ] = self.enable_performance_insights
        if self.performance_insights_kms_key_id:
            not_null_args[
                "PerformanceInsightsKMSKeyId"
            ] = self.performance_insights_kms_key_id
        if self.performance_insights_retention_period:
            not_null_args[
                "PerformanceInsightsRetentionPeriod"
            ] = self.performance_insights_retention_period
        if self.serverless_v2_scaling_configuration:
            not_null_args[
                "ServerlessV2ScalingConfiguration"
            ] = self.serverless_v2_scaling_configuration
        if self.network_type:
            not_null_args["NetworkType"] = self.network_type
        if self.db_system_id:
            not_null_args["DBSystemId"] = self.db_system_id
        if self.source_region:
            not_null_args["SourceRegion"] = self.source_region

        # Step 3: Create CacheCluster
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_db_cluster(
                DBClusterIdentifier=self.get_db_cluster_identifier(),
                Engine=self.engine,
                **not_null_args,
            )
            logger.debug(f"CacheCluster: {create_response}")
            database_dict = create_response.get("DBCluster", {})

            # Validate database creation
            if database_dict is not None:
                print_info(f"CacheCluster created: {self.get_db_cluster_identifier()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:

        db_instances_created = []
        if self.db_instances is not None:
            for db_instance in self.db_instances:
                db_instance.db_cluster_identifier = self.get_db_cluster_identifier()
                if db_instance._create(aws_client):  # type: ignore
                    db_instances_created.append(db_instance)

        # Wait for CacheCluster to be created
        if self.wait_for_creation:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be active.")
                waiter = self.get_service_client(aws_client).get_waiter(
                    "db_cluster_available"
                )
                waiter.wait(
                    DBClusterIdentifier=self.get_db_cluster_identifier(),
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error("Waiter failed.")
                print_error(e)

            # Wait for DbInstances to be created
            for db_instance in db_instances_created:
                db_instance.post_create(aws_client)

        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the CacheCluster

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            db_cluster_identifier = self.get_db_cluster_identifier()
            describe_response = service_client.describe_db_clusters(
                DBClusterIdentifier=db_cluster_identifier
            )
            logger.debug(f"CacheCluster: {describe_response}")
            db_clusters_list = describe_response.get("DBClusters", None)

            if db_clusters_list is not None and isinstance(db_clusters_list, list):
                for _db_cluster in db_clusters_list:
                    _cluster_identifier = _db_cluster.get("DBClusterIdentifier", None)
                    if _cluster_identifier == db_cluster_identifier:
                        self.active_resource = _db_cluster
                        break
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the CacheCluster

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None

        # Step 1: Delete DbInstances
        if self.db_instances is not None:
            for db_instance in self.db_instances:
                db_instance._delete(aws_client)

        # Step 2: Delete CacheCluster
        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.final_db_snapshot_identifier:
            not_null_args[
                "FinalDBSnapshotIdentifier"
            ] = self.final_db_snapshot_identifier

        try:
            db_cluster_identifier = self.get_db_cluster_identifier()
            delete_response = service_client.delete_db_cluster(
                DBClusterIdentifier=db_cluster_identifier,
                SkipFinalSnapshot=self.skip_final_snapshot,
                **not_null_args,
            )
            logger.debug(f"CacheCluster: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def post_delete(self, aws_client: AwsApiClient) -> bool:

        # Wait for CacheCluster to be deleted
        if self.wait_for_deletion:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
                waiter = self.get_service_client(aws_client).get_waiter(
                    "db_cluster_deleted"
                )
                waiter.wait(
                    DBClusterIdentifier=self.get_db_cluster_identifier(),
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error("Waiter failed.")
                print_error(e)
        return True
