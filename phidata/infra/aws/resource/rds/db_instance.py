from pathlib import Path
from typing import Optional, Any, Dict, List, Literal, Union

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.infra.aws.resource.rds.db_subnet_group import DbSubnetGroup
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class DbInstance(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html

    The DBInstance can be an RDS DB instance, or it can be a DB instance in an Aurora DB cluster.
    """

    resource_type = "DbInstance"
    service_name = "rds"

    # Name of the db instance.
    name: str
    # The name of the database engine to be used for this instance.
    engine: Union[
        str,
        Literal[
            "aurora",
            "aurora-mysql",
            "aurora-postgresql",
            "custom-oracle-ee",
            "custom-sqlserver-ee",
            "custom-sqlserver-se",
            "custom-sqlserver-web",
            "mariadb",
            "mysql",
            "oracle-ee",
            "oracle-ee-cdb",
            "oracle-se2",
            "oracle-se2-cdb",
            "postgres",
            "sqlserver-ee",
            "sqlserver-se",
            "sqlserver-ex",
            "sqlserver-web",
        ],
    ]
    # Compute and memory capacity of the DB instance, for example db.m5.large.
    db_instance_class: Optional[str] = None

    # This is the name of the database to create when the DB instance is created.
    # Note: The meaning of this parameter differs according to the database engine you use.
    # Provide DB_NAME here or as DB_NAME in secrets_file
    db_name: Optional[str] = None
    # The DB instance identifier. This parameter is stored as a lowercase string.
    # If None, use the name as the db_instance_identifier
    # Constraints:
    # - Must contain from 1 to 63 letters, numbers, or hyphens.
    # - First character must be a letter.
    # - Can't end with a hyphen or contain two consecutive hyphens.
    db_instance_identifier: Optional[str] = None
    # The amount of storage in gibibytes (GiB) to allocate for the DB instance.
    allocated_storage: Optional[int] = None

    # The name for the master user.
    # Provide MASTER_USERNAME here or as MASTER_USERNAME in secrets_file
    master_username: Optional[str] = None
    # The password for the master user.
    # The password can include any printable ASCII character except "/", """, or "@".
    # Provide MASTER_USER_PASSWORD here or as MASTER_USER_PASSWORD in secrets_file
    master_user_password: Optional[str] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None

    # A list of DB security groups to associate with this DB instance.
    # This setting applies to the legacy EC2-Classic platform, which no longer creates new DB instances.
    # Use the VpcSecurityGroupIds setting instead.
    db_security_groups: Optional[List[str]] = None
    # A list of Amazon EC2 VPC security groups to associate with this DB instance.
    vpc_security_group_ids: Optional[List[str]] = None
    # If vpc_security_group_ids is None,
    # Read the security_group_id from vpc_stack
    vpc_stack: Optional[CloudFormationStack] = None

    # The Availability Zone (AZ) where the database will be created.
    availability_zone: Optional[str] = None
    # A DB subnet group to associate with this DB instance.
    db_subnet_group_name: Optional[str] = None
    # If db_subnet_group_name is None,
    # Read the db_subnet_group_name from db_subnet_group
    db_subnet_group: Optional[DbSubnetGroup] = None

    # The time range each week during which system maintenance can occur, in Universal Coordinated Time (UTC).
    preferred_maintenance_window: Optional[str] = None
    # The name of the DB parameter group to associate with this DB instance.
    db_parameter_group_name: Optional[str] = None
    backup_retention_period: Optional[int] = None
    preferred_backup_window: Optional[str] = None
    # The port number on which the database accepts connections.
    port: Optional[int] = None
    # A value that indicates whether the DB instance is a Multi-AZ deployment.
    # You can't set the AvailabilityZone parameter if the DB instance is a Multi-AZ deployment.
    multi_az: Optional[bool] = None
    # The version number of the database engine to use.
    engine_version: Optional[str] = None
    auto_minor_version_upgrade: Optional[bool] = None
    license_model: Optional[str] = None
    iops: Optional[int] = None
    option_group_name: Optional[str] = None
    character_set_name: Optional[str] = None
    nchar_character_set_name: Optional[str] = None
    # A value that indicates whether the DB instance is publicly accessible.
    # When the DB instance is publicly accessible, its Domain Name System (DNS) endpoint resolves to the private IP
    # from within the DB instance's virtual private cloud (VPC). It resolves to the public IP address from outside
    # the DB instance's VPC. Access to the DB instance is ultimately controlled by the security group it uses.
    # That public access is not permitted if the security group assigned to the DB instance doesn't permit it.
    #
    # When the DB instance isn't publicly accessible, it is an internal DB instance with a DNS name that resolves
    # to a private IP address.
    publicly_accessible: Optional[bool] = None
    tags: Optional[List[Dict[str, str]]] = None
    # The identifier of the DB cluster that the instance will belong to.
    db_cluster_identifier: Optional[str] = None
    # Specifies the storage type to be associated with the DB instance.
    # Valid values: gp2 | gp3 | io1 | standard
    # If you specify io1 or gp3 , you must also include a value for the Iops parameter.
    # Default: io1 if the Iops parameter is specified, otherwise gp2
    storage_type: Optional[str] = None
    tde_credential_arn: Optional[str] = None
    tde_credential_password: Optional[str] = None
    storage_encrypted: Optional[bool] = None
    kms_key_id: Optional[str] = None
    domain: Optional[str] = None
    copy_tags_to_snapshot: Optional[bool] = None
    monitoring_interval: Optional[int] = None
    monitoring_role_arn: Optional[str] = None
    domain_iamrole_name: Optional[str] = None
    promotion_tier: Optional[int] = None
    timezone: Optional[str] = None
    enable_iamdatabase_authentication: Optional[bool] = None
    enable_performance_insights: Optional[bool] = None
    performance_insights_kmskey_id: Optional[str] = None
    performance_insights_retention_period: Optional[int] = None
    enable_cloudwatch_logs_exports: Optional[List[str]] = None
    processor_features: Optional[List[Dict[str, str]]] = None
    # A value that indicates whether the DB instance has deletion protection enabled. The database can't be deleted
    # when deletion protection is enabled. By default, deletion protection isn't enabled.
    deletion_protection: Optional[bool] = None
    # The upper limit in gibibytes (GiB) to which Amazon RDS can automatically scale the storage of the DB instance.
    max_allocated_storage: Optional[int] = None
    enable_customer_owned_ip: Optional[bool] = None
    custom_iam_instance_profile: Optional[str] = None
    backup_target: Optional[str] = None
    network_type: Optional[str] = None
    storage_throughput: Optional[int] = None

    # Skip the creation of a final DB cluster snapshot before the DB cluster is deleted.
    # If skip_final_snapshot = True, no DB cluster snapshot is created.
    # If skip_final_snapshot = None, a DB cluster snapshot is created before the DB cluster is deleted.
    #
    # You must specify a FinalDBSnapshotIdentifier parameter
    # if skip_final_snapshot = None.
    skip_final_snapshot: Optional[bool] = True
    final_db_snapshot_identifier: Optional[str] = None

    # Cache secret_data
    cached_secret_data: Optional[Dict[str, Any]] = None

    def get_db_instance_identifier(self):
        return self.db_instance_identifier or self.name

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

    def get_db_name(self) -> Optional[str]:
        db_name = self.db_name
        if db_name is None and self.secrets_file is not None:
            # read from secrets_file
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_name = secret_data.get("DB_NAME", db_name)
                if db_name is None:
                    db_name = secret_data.get("DATABASE_NAME", db_name)
        return db_name

    def get_database_name(self) -> Optional[str]:
        # Alias for get_db_name because db_instances use `db_name` and db_clusters use `database_name`
        return self.get_db_name()

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the DbInstance

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
        db_name = self.get_db_name()
        if db_name:
            not_null_args["DBName"] = db_name

        if self.allocated_storage:
            not_null_args["AllocatedStorage"] = self.allocated_storage
        if self.db_instance_class:
            not_null_args["DBInstanceClass"] = self.db_instance_class

        master_username = self.get_master_username()
        if master_username:
            not_null_args["MasterUsername"] = master_username
        master_user_password = self.get_master_user_password()
        if master_user_password:
            not_null_args["MasterUserPassword"] = master_user_password

        if self.db_security_groups is not None:
            not_null_args["DBSecurityGroups"] = self.db_security_groups
        if vpc_security_group_ids is not None:
            not_null_args["VpcSecurityGroupIds"] = vpc_security_group_ids
        if self.availability_zone is not None:
            not_null_args["AvailabilityZone"] = self.availability_zone
        if db_subnet_group_name is not None:
            not_null_args["DBSubnetGroupName"] = db_subnet_group_name

        if self.preferred_maintenance_window:
            not_null_args[
                "PreferredMaintenanceWindow"
            ] = self.preferred_maintenance_window
        if self.db_parameter_group_name:
            not_null_args["DBParameterGroupName"] = self.db_parameter_group_name
        if self.backup_retention_period:
            not_null_args["BackupRetentionPeriod"] = self.backup_retention_period
        if self.preferred_backup_window:
            not_null_args["PreferredBackupWindow"] = self.preferred_backup_window
        if self.port:
            not_null_args["Port"] = self.port
        if self.multi_az:
            not_null_args["MultiAZ"] = self.multi_az
        if self.engine_version:
            not_null_args["EngineVersion"] = self.engine_version
        if self.auto_minor_version_upgrade:
            not_null_args["AutoMinorVersionUpgrade"] = self.auto_minor_version_upgrade
        if self.license_model:
            not_null_args["LicenseModel"] = self.license_model
        if self.iops:
            not_null_args["Iops"] = self.iops
        if self.option_group_name:
            not_null_args["OptionGroupName"] = self.option_group_name
        if self.character_set_name:
            not_null_args["CharacterSetName"] = self.character_set_name
        if self.nchar_character_set_name:
            not_null_args["NcharCharacterSetName"] = self.nchar_character_set_name
        if self.publicly_accessible:
            not_null_args["PubliclyAccessible"] = self.publicly_accessible
        if self.tags:
            not_null_args["Tags"] = self.tags
        if self.db_cluster_identifier:
            not_null_args["DBClusterIdentifier"] = self.db_cluster_identifier
        if self.storage_type:
            not_null_args["StorageType"] = self.storage_type
        if self.tde_credential_arn:
            not_null_args["TdeCredentialArn"] = self.tde_credential_arn
        if self.tde_credential_password:
            not_null_args["TdeCredentialPassword"] = self.tde_credential_password
        if self.storage_encrypted:
            not_null_args["StorageEncrypted"] = self.storage_encrypted
        if self.kms_key_id:
            not_null_args["KmsKeyId"] = self.kms_key_id
        if self.domain:
            not_null_args["Domain"] = self.domain
        if self.copy_tags_to_snapshot:
            not_null_args["CopyTagsToSnapshot"] = self.copy_tags_to_snapshot
        if self.monitoring_interval:
            not_null_args["MonitoringInterval"] = self.monitoring_interval
        if self.monitoring_role_arn:
            not_null_args["MonitoringRoleArn"] = self.monitoring_role_arn
        if self.domain_iamrole_name:
            not_null_args["DomainIAMRoleName"] = self.domain_iamrole_name
        if self.promotion_tier:
            not_null_args["PromotionTier"] = self.promotion_tier
        if self.timezone:
            not_null_args["Timezone"] = self.timezone
        if self.enable_iamdatabase_authentication:
            not_null_args[
                "EnableIAMDatabaseAuthentication"
            ] = self.enable_iamdatabase_authentication
        if self.enable_performance_insights:
            not_null_args[
                "EnablePerformanceInsights"
            ] = self.enable_performance_insights
        if self.performance_insights_kmskey_id:
            not_null_args[
                "PerformanceInsightsKMSKeyId"
            ] = self.performance_insights_kmskey_id
        if self.performance_insights_retention_period:
            not_null_args[
                "PerformanceInsightsRetentionPeriod"
            ] = self.performance_insights_retention_period
        if self.enable_cloudwatch_logs_exports:
            not_null_args[
                "EnableCloudwatchLogsExports"
            ] = self.enable_cloudwatch_logs_exports
        if self.processor_features:
            not_null_args["ProcessorFeatures"] = self.processor_features
        if self.deletion_protection:
            not_null_args["DeletionProtection"] = self.deletion_protection
        if self.max_allocated_storage:
            not_null_args["MaxAllocatedStorage"] = self.max_allocated_storage
        if self.enable_customer_owned_ip:
            not_null_args["EnableCustomerOwnedIp"] = self.enable_customer_owned_ip
        if self.custom_iam_instance_profile:
            not_null_args["CustomIamInstanceProfile"] = self.custom_iam_instance_profile
        if self.backup_target:
            not_null_args["BackupTarget"] = self.backup_target
        if self.network_type:
            not_null_args["NetworkType"] = self.network_type
        if self.storage_throughput:
            not_null_args["StorageThroughput"] = self.storage_throughput

        # Step 3: Create DbInstance
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_db_instance(
                DBInstanceIdentifier=self.get_db_instance_identifier(),
                Engine=self.engine,
                **not_null_args,
            )
            logger.debug(f"DbInstance: {create_response}")
            resource_dict = create_response.get("DBInstance", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"DbInstance created: {self.get_db_instance_identifier()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:

        # Wait for DbInstance to be created
        if self.wait_for_creation:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be active.")
                waiter = self.get_service_client(aws_client).get_waiter(
                    "db_instance_available"
                )
                waiter.wait(
                    DBInstanceIdentifier=self.get_db_instance_identifier(),
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error("Waiter failed.")
                print_error(e)
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the DbInstance

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            db_instance_identifier = self.get_db_instance_identifier()
            describe_response = service_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            logger.debug(f"DbInstance: {describe_response}")
            resources_list = describe_response.get("DBInstances", None)

            if resources_list is not None and isinstance(resources_list, list):
                for _db_cluster in resources_list:
                    _cluster_identifier = _db_cluster.get("DBInstanceIdentifier", None)
                    if _cluster_identifier == db_instance_identifier:
                        self.active_resource = _db_cluster
                        break
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the DbInstance

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.final_db_snapshot_identifier:
            not_null_args[
                "FinalDBSnapshotIdentifier"
            ] = self.final_db_snapshot_identifier

        try:
            db_instance_identifier = self.get_db_instance_identifier()
            delete_response = service_client.delete_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                SkipFinalSnapshot=self.skip_final_snapshot,
                **not_null_args,
            )
            logger.debug(f"Delete Response: {delete_response}")
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

        # Wait for DbInstance to be deleted
        if self.wait_for_deletion:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
                waiter = self.get_service_client(aws_client).get_waiter(
                    "db_instance_deleted"
                )
                waiter.wait(
                    DBInstanceIdentifier=self.get_db_instance_identifier(),
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error("Waiter failed.")
                print_error(e)
        return True
