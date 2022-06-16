# from typing import Optional, Any, List, Dict
#
# from botocore.exceptions import ClientError
#
# from phidata.infra.aws.api_client import AwsApiClient
# from phidata.infra.aws.resource.base import AwsResource
# from phidata.infra.aws.resource.iam.policy import IamPolicy
# from phidata.utils.cli_console import print_info, print_error
# from phidata.utils.log import logger
#
#
# class IamGroup(AwsResource):
#     """
#     # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#group
#     """
#
#     resource_type = "IamGroup"
#     service_name = "iam"
#
#     # GroupName: The name of the group to create.
#     name: str
#     # The trust relationship policy document that grants an entity permission to assume the group.
#     assume_role_policy_document: str
#     # The path to the group. This parameter is optional. If it is not included, it defaults to a slash (/).
#     path: Optional[str] = None
#     # A description of the group.
#     description: Optional[str] = None
#     # The maximum session duration (in seconds) that you want to set for the specified group.
#     # If you do not specify a value for this setting, the default maximum of one hour is applied.
#     # This setting can have a value from 1 hour to 12 hours.
#     max_session_duration: Optional[int] = None
#     # The ARN of the policy that is used to set the permissions boundary for the group.
#     permissions_boundary: Optional[str] = None
#     # A list of tags that you want to attach to the new group. Each tag consists of a key name and an associated value.
#     tags: Optional[List[Dict[str, str]]] = None
#
#     # List of IAM policies to
#     # attach to the group after it is created
#     policies: Optional[List[IamPolicy]] = None
#     # List of IAM policy ARNs (Amazon Resource Name) to
#     # attach to the group after it is created
#     policy_arns: Optional[List[str]] = None
#
#     # The Amazon Resource Name (ARN) specifying the group.
#     # To get the arn, use get_arn() function
#     arn: Optional[str] = None
#
#     def _create(self, aws_client: AwsApiClient) -> bool:
#         """Creates the IamGroup
#
#         Args:
#             aws_client: The AwsApiClient for the current cluster
#         """
#
#         print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
#         try:
#             # create a dict of args which are not null, otherwise aws type validation fails
#             not_null_args: Dict[str, Any] = {}
#             if self.path:
#                 not_null_args["Path"] = self.path
#             if self.description:
#                 not_null_args["Description"] = self.description
#             if self.max_session_duration:
#                 not_null_args["MaxSessionDuration"] = self.max_session_duration
#             if self.permissions_boundary:
#                 not_null_args["PermissionsBoundary"] = self.permissions_boundary
#             if self.tags:
#                 not_null_args["Tags"] = self.tags
#
#             # Create Group
#             service_resource = self.get_service_resource(aws_client)
#             group = service_resource.create_role(
#                 GroupName=self.name,
#                 AssumeGroupPolicyDocument=self.assume_role_policy_document,
#                 **not_null_args,
#             )
#             # logger.debug(f"Group: {group}")
#
#             # Validate Group creation
#             create_date = group.create_date
#             self.arn = group.arn
#             logger.debug(f"create_date: {create_date}")
#             logger.debug(f"arn: {self.arn}")
#             if create_date is not None:
#                 print_info(f"Group created: {self.name}")
#                 self.active_resource = group
#                 return True
#             print_error("Group could not be created")
#         except Exception as e:
#             print_error(f"{self.get_resource_type()} could not be created.")
#             print_error(e)
#         return False
#
#     def post_create(self, aws_client: AwsApiClient) -> bool:
#         # Wait for Group to be created
#         if self.wait_for_creation:
#             try:
#                 print_info(f"Waiting for {self.get_resource_type()} to be created.")
#                 waiter = self.get_service_client(aws_client).get_waiter("role_exists")
#                 waiter.wait(
#                     GroupName=self.name,
#                     WaiterConfig={
#                         "Delay": self.waiter_delay,
#                         "MaxAttempts": self.waiter_max_attempts,
#                     },
#                 )
#             except Exception as e:
#                 print_error("Waiter failed.")
#                 print_error(e)
#         # Attach policy arns to group
#         if self.active_resource is not None and self.policy_arns is not None:
#             self.attach_policy_arns(aws_client)
#         # Attach policies to group
#         if self.active_resource is not None and self.policies is not None:
#             self.attach_policies(aws_client)
#         return True
#
#     def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
#         """Returns the IamGroup
#
#         Args:
#             aws_client: The AwsApiClient for the current cluster
#         """
#         logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
#         try:
#             service_resource = self.get_service_resource(aws_client)
#             group = service_resource.Group(name=self.name)
#             group.load()
#             create_date = group.create_date
#             self.arn = group.arn
#             logger.debug(f"create_date: {create_date}")
#             logger.debug(f"arn: {self.arn}")
#             if create_date is not None:
#                 logger.debug(f"Group found: {group.role_name}")
#                 self.active_resource = group
#         except ClientError as ce:
#             logger.debug(f"ClientError: {ce}")
#             pass
#         except Exception as e:
#             print_error(f"Error reading {self.get_resource_type()}.")
#             print_error(e)
#         return self.active_resource
#
#     def _delete(self, aws_client: AwsApiClient) -> bool:
#         """Deletes the IamGroup
#
#         Args:
#             aws_client: The AwsApiClient for the current cluster
#         """
#
#         print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
#         try:
#             group = self._read(aws_client)
#             # logger.debug(f"Group: {group}")
#             # logger.debug(f"Group type: {type(group)}")
#             self.active_resource = None
#
#             if group is None:
#                 logger.warning(f"No {self.get_resource_type()} to delete")
#                 return True
#
#             # detach all policies
#             policies = group.attached_policies.all()
#             for policy in policies:
#                 print_info(f"Detaching policy: {policy}")
#                 group.detach_policy(PolicyArn=policy.arn)
#
#             # detach all instance profiles
#             profiles = group.instance_profiles.all()
#             for profile in profiles:
#                 print_info(f"Removing group from profile: {profile}")
#                 profile.remove_role(GroupName=group.name)
#
#             # delete group
#             group.delete()
#             print_info(
#                 f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
#             )
#             return True
#         except Exception as e:
#             print_error(f"{self.get_resource_type()} could not be deleted.")
#             print_error("Please try again or delete resources manually.")
#             print_error(e)
#         return False
#
#     def attach_policy_arns(self, aws_client: AwsApiClient) -> bool:
#         """
#         Attaches the specified managed policy to the specified IAM group.
#         When you attach a managed policy to a group, the managed policy becomes part of the
#         group's permission (access) policy.
#
#         Returns:
#             True if operation was successful
#         """
#         if self.policy_arns is None:
#             return True
#
#         group = self._read(aws_client)
#         if group is None:
#             logger.warning(f"No {self.get_resource_type()} to attach")
#             return True
#         try:
#             # logger.debug("Attaching managed policies to group")
#             for arn in self.policy_arns:
#                 if isinstance(arn, str):
#                     group.attach_policy(PolicyArn=arn)
#                     print_info(f"Attaching policy to {group.role_name}: {arn}")
#             return True
#         except Exception as e:
#             print_error(e)
#         return False
#
#     def attach_policies(self, aws_client: AwsApiClient) -> bool:
#         """
#         Returns:
#             True if operation was successful
#         """
#         if self.policies is None:
#             return True
#
#         group = self._read(aws_client)
#         if group is None:
#             logger.warning(f"No {self.get_resource_type()} to attach")
#             return True
#         try:
#             logger.debug("Attaching managed policies to group")
#             for policy in self.policies:
#                 if policy.arn is None:
#                     policy.create(aws_client)
#                 if policy.arn is not None:
#                     group.attach_policy(PolicyArn=policy.arn)
#                     print_info(f"Attaching policy to {group.role_name}: {policy.arn}")
#             return True
#         except Exception as e:
#             print_error(e)
#         return False
#
#     def get_arn(self, aws_client: AwsApiClient) -> Optional[str]:
#         group = self._read(aws_client)
#         if group is None:
#             return None
#
#         self.arn = group.arn
#         return self.arn
