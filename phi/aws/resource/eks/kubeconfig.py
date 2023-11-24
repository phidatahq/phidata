from pathlib import Path
from typing import Optional, Any, Dict

from phi.aws.api_client import AwsApiClient
from phi.k8s.enums.api_version import ApiVersion
from phi.aws.resource.base import AwsResource
from phi.aws.resource.iam.role import IamRole
from phi.aws.resource.eks.cluster import EksCluster
from phi.k8s.resource.kubeconfig import (
    Kubeconfig,
    KubeconfigCluster,
    KubeconfigClusterConfig,
    KubeconfigContext,
    KubeconfigContextSpec,
    KubeconfigUser,
)
from phi.cli.console import print_info
from phi.utils.log import logger


class EksKubeconfig(AwsResource):
    resource_type: Optional[str] = "Kubeconfig"
    service_name: str = "na"

    # Optional: kubeconfig name, used for filtering during phi ws up/down
    name: str = "kubeconfig"
    # Required: EksCluster to generate the kubeconfig for
    eks_cluster: EksCluster
    # Required: Path to kubeconfig file
    kubeconfig_path: Path = Path.home().joinpath(".kube").joinpath("config").resolve()

    # Optional: cluster_name to use in kubeconfig, defaults to eks_cluster.name
    kubeconfig_cluster_name: Optional[str] = None
    # Optional: cluster_user to use in kubeconfig, defaults to eks_cluster.name
    kubeconfig_cluster_user: Optional[str] = None
    # Optional: cluster_context to use in kubeconfig, defaults to eks_cluster.name
    kubeconfig_cluster_context: Optional[str] = None

    # Optional: role to assume when signing the token
    kubeconfig_role: Optional[IamRole] = None
    # Optional: role arn to assume when signing the token
    kubeconfig_role_arn: Optional[str] = None

    # Dont delete this EksKubeconfig from the kubeconfig file
    skip_delete: bool = True
    # Mark use_cache as False so the kubeconfig is re-created
    # every time phi ws up/down is run
    use_cache: bool = False

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the EksKubeconfig

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            return self.write_kubeconfig(aws_client=aws_client)
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be created.")
            logger.error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Reads the EksKubeconfig

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            kubeconfig_path = self.get_kubeconfig_path()
            if kubeconfig_path is not None:
                return Kubeconfig.read_from_file(kubeconfig_path)
        except Exception as e:
            logger.error(f"Error reading {self.get_resource_type()}.")
            logger.error(e)
        return self.active_resource

    def _update(self, aws_client: AwsApiClient) -> bool:
        """Updates the EksKubeconfig

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Updating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            return self.write_kubeconfig(aws_client=aws_client)
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be updated.")
            logger.error(e)
        return False

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the EksKubeconfig

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            return self.clean_kubeconfig(aws_client=aws_client)
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be deleted.")
            logger.error(e)
        return False

    def get_kubeconfig_path(self) -> Optional[Path]:
        return self.kubeconfig_path or self.eks_cluster.kubeconfig_path

    def get_kubeconfig_cluster_name(self) -> str:
        return self.kubeconfig_cluster_name or self.eks_cluster.get_kubeconfig_cluster_name()

    def get_kubeconfig_user_name(self) -> str:
        return self.kubeconfig_cluster_user or self.eks_cluster.get_kubeconfig_user_name()

    def get_kubeconfig_context_name(self) -> str:
        return self.kubeconfig_cluster_context or self.eks_cluster.get_kubeconfig_context_name()

    def get_kubeconfig_role(self) -> Optional[IamRole]:
        return self.kubeconfig_role or self.eks_cluster.kubeconfig_role

    def get_kubeconfig_role_arn(self) -> Optional[str]:
        return self.kubeconfig_role_arn or self.eks_cluster.kubeconfig_role_arn

    def write_kubeconfig(self, aws_client: AwsApiClient) -> bool:
        # Step 1: Get the EksCluster to generate the kubeconfig for
        eks_cluster = self.eks_cluster._read(aws_client=aws_client)  # type: ignore
        if eks_cluster is None:
            logger.warning(f"EKSCluster not available: {self.eks_cluster.name}")
            return False

        # Step 2: Get EksCluster cert, endpoint & arn
        try:
            cluster_cert = eks_cluster.get("cluster", {}).get("certificateAuthority", {}).get("data", None)
            logger.debug(f"cluster_cert: {cluster_cert}")

            cluster_endpoint = eks_cluster.get("cluster", {}).get("endpoint", None)
            logger.debug(f"cluster_endpoint: {cluster_endpoint}")

            cluster_arn = eks_cluster.get("cluster", {}).get("arn", None)
            logger.debug(f"cluster_arn: {cluster_arn}")
        except Exception as e:
            logger.error("Cannot read EKSCluster")
            logger.error(e)
            return False

        # Step 3: Build Kubeconfig components
        # 3.1 Build KubeconfigCluster config
        cluster_name = self.get_kubeconfig_cluster_name()
        new_cluster = KubeconfigCluster(
            name=cluster_name,
            cluster=KubeconfigClusterConfig(
                server=str(cluster_endpoint),
                certificate_authority_data=str(cluster_cert),
            ),
        )

        # 3.2 Build KubeconfigUser config
        new_user_exec_args = ["eks", "get-token", "--cluster-name", cluster_name]
        if aws_client.aws_region is not None:
            new_user_exec_args.extend(["--region", aws_client.aws_region])
        # Assume the role if the role_arn is provided
        role = self.get_kubeconfig_role()
        role_arn = self.get_kubeconfig_role_arn()
        if role_arn is not None:
            new_user_exec_args.extend(["--role-arn", role_arn])
        # Otherwise if role is provided, use that to get the role arn
        elif role is not None:
            _arn = role.get_arn(aws_client=aws_client)
            if _arn is not None:
                new_user_exec_args.extend(["--role-arn", _arn])

        new_user_exec: Dict[str, Any] = {
            "apiVersion": ApiVersion.CLIENT_AUTHENTICATION_V1BETA1.value,
            "command": "aws",
            "args": new_user_exec_args,
        }
        if aws_client.aws_profile is not None:
            new_user_exec["env"] = [{"name": "AWS_PROFILE", "value": aws_client.aws_profile}]

        new_user = KubeconfigUser(
            name=self.get_kubeconfig_user_name(),
            user={"exec": new_user_exec},
        )

        # 3.3 Build KubeconfigContext config
        new_context = KubeconfigContext(
            name=self.get_kubeconfig_context_name(),
            context=KubeconfigContextSpec(
                cluster=new_cluster.name,
                user=new_user.name,
            ),
        )
        current_context = new_context.name

        # Step 4: Get existing Kubeconfig
        kubeconfig_path = self.get_kubeconfig_path()
        if kubeconfig_path is None:
            logger.error("kubeconfig_path is None")
            return False

        kubeconfig: Optional[Any] = Kubeconfig.read_from_file(kubeconfig_path)

        # Step 5: Parse through the existing config to determine if
        # an update is required. By the end of this logic
        # if write_kubeconfig = False then no changes to kubeconfig are needed
        # if write_kubeconfig = True then we should write the kubeconfig file
        write_kubeconfig = False

        # Kubeconfig exists and is valid
        if kubeconfig is not None and isinstance(kubeconfig, Kubeconfig):
            # Update Kubeconfig.clusters:
            # If a cluster with the same name exists in Kubeconfig.clusters
            #   - check if server and cert values match, if not, remove the existing cluster
            #   and add the new cluster config. Mark cluster_config_exists = True
            # If a cluster with the same name does not exist in Kubeconfig.clusters
            #   - add the new cluster config
            cluster_config_exists = False
            for idx, _cluster in enumerate(kubeconfig.clusters, start=0):
                if _cluster.name == new_cluster.name:
                    cluster_config_exists = True
                    if (
                        _cluster.cluster.server != new_cluster.cluster.server
                        or _cluster.cluster.certificate_authority_data != new_cluster.cluster.certificate_authority_data
                    ):
                        logger.debug("Kubeconfig.cluster mismatch, updating cluster config")
                        kubeconfig.clusters.pop(idx)
                        # logger.debug(
                        #     f"removed_cluster_config: {removed_cluster_config}"
                        # )
                        kubeconfig.clusters.append(new_cluster)
                        write_kubeconfig = True
            if not cluster_config_exists:
                logger.debug("Adding Kubeconfig.cluster")
                kubeconfig.clusters.append(new_cluster)
                write_kubeconfig = True

            # Update Kubeconfig.users:
            # If a user with the same name exists in Kubeconfig.users -
            #   check if user spec matches, if not, remove the existing user
            #   and add the new user config. Mark user_config_exists = True
            # If a user with the same name does not exist in Kubeconfig.users -
            #   add the new user config
            user_config_exists = False
            for idx, _user in enumerate(kubeconfig.users, start=0):
                if _user.name == new_user.name:
                    user_config_exists = True
                    if _user.user != new_user.user:
                        logger.debug("Kubeconfig.user mismatch, updating user config")
                        kubeconfig.users.pop(idx)
                        # logger.debug(f"removed_user_config: {removed_user_config}")
                        kubeconfig.users.append(new_user)
                        write_kubeconfig = True
            if not user_config_exists:
                logger.debug("Adding Kubeconfig.user")
                kubeconfig.users.append(new_user)
                write_kubeconfig = True

            # Update Kubeconfig.contexts:
            # If a context with the same name exists in Kubeconfig.contexts -
            #   check if context spec matches, if not, remove the existing context
            #   and add the new context. Mark context_config_exists = True
            # If a context with the same name does not exist in Kubeconfig.contexts -
            #   add the new context config
            context_config_exists = False
            for idx, _context in enumerate(kubeconfig.contexts, start=0):
                if _context.name == new_context.name:
                    context_config_exists = True
                    if _context.context != new_context.context:
                        logger.debug("Kubeconfig.context mismatch, updating context config")
                        kubeconfig.contexts.pop(idx)
                        # logger.debug(
                        #     f"removed_context_config: {removed_context_config}"
                        # )
                        kubeconfig.contexts.append(new_context)
                        write_kubeconfig = True
            if not context_config_exists:
                logger.debug("Adding Kubeconfig.context")
                kubeconfig.contexts.append(new_context)
                write_kubeconfig = True

            if kubeconfig.current_context is None or kubeconfig.current_context != current_context:
                logger.debug("Updating Kubeconfig.current_context")
                kubeconfig.current_context = current_context
                write_kubeconfig = True
        else:
            # Kubeconfig does not exist or is not valid
            # Create a new Kubeconfig
            logger.info("Creating new Kubeconfig")
            kubeconfig = Kubeconfig(
                clusters=[new_cluster],
                users=[new_user],
                contexts=[new_context],
                current_context=current_context,
            )
            write_kubeconfig = True

        # if kubeconfig:
        #     logger.debug("Kubeconfig:\n{}".format(kubeconfig.json(exclude_none=True, by_alias=True, indent=4)))

        # Step 5: Write Kubeconfig if an update is made
        if write_kubeconfig:
            return kubeconfig.write_to_file(kubeconfig_path)
        else:
            logger.info("Kubeconfig up-to-date")
        return True

    def clean_kubeconfig(self, aws_client: AwsApiClient) -> bool:
        logger.debug(f"TO_DO: Cleaning kubeconfig at {str(self.kubeconfig_path)}")
        return True
