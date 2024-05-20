from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import FilePath

from phi.resource.base import ResourceBase
from phi.k8s.api_client import K8sApiClient
from phi.k8s.constants import DEFAULT_K8S_NAMESPACE
from phi.k8s.helm.cli import run_shell_command
from phi.cli.console import print_info
from phi.utils.log import logger


class HelmChart(ResourceBase):
    chart: str
    set: Optional[Dict[str, Any]] = None
    values: Optional[Union[FilePath, List[FilePath]]] = None
    flags: Optional[List[str]] = None
    namespace: Optional[str] = None
    create_namespace: bool = True

    repo: Optional[str] = None
    update_repo_before_install: bool = True

    k8s_client: Optional[K8sApiClient] = None
    resource_type: str = "Chart"

    def get_resource_name(self) -> str:
        return self.name

    def get_namespace(self) -> str:
        if self.namespace is not None:
            return self.namespace
        return DEFAULT_K8S_NAMESPACE

    def get_k8s_client(self) -> K8sApiClient:
        if self.k8s_client is not None:
            return self.k8s_client
        self.k8s_client = K8sApiClient()
        return self.k8s_client

    def _read(self, k8s_client: K8sApiClient) -> Any:
        try:
            logger.info(f"Getting helm chart: {self.name}\n")
            get_args = ["helm", "get", "manifest", self.name]
            if self.namespace is not None:
                get_args.append(f"--namespace={self.namespace}")
            get_result = run_shell_command(get_args, display_result=False, display_error=False)
            if get_result.stdout:
                import yaml

                return yaml.safe_load_all(get_result.stdout)
        except Exception:
            pass
        return None

    def read(self, k8s_client: K8sApiClient) -> Any:
        # Step 1: Use cached value if available
        if self.use_cache and self.active_resource is not None:
            return self.active_resource

        # Step 2: Skip resource creation if skip_read = True
        if self.skip_read:
            print_info(f"Skipping read: {self.get_resource_name()}")
            return True

        # Step 3: Read resource
        client: K8sApiClient = k8s_client or self.get_k8s_client()
        return self._read(client)

    def is_active(self, k8s_client: K8sApiClient) -> bool:
        """Returns True if the resource is active on the k8s cluster"""
        self.active_resource = self._read(k8s_client=k8s_client)
        return True if self.active_resource is not None else False

    def _create(self, k8s_client: K8sApiClient) -> bool:
        if self.repo:
            try:
                logger.info(f"Adding helm repo: {self.name} {self.repo}\n")
                add_args = ["helm", "repo", "add", self.name, self.repo]
                run_shell_command(add_args)

                if self.update_repo_before_install:
                    logger.info(f"Updating helm repo: {self.name}\n")
                    update_args = ["helm", "repo", "update", self.name]
                    run_shell_command(update_args)
            except Exception as e:
                logger.error(f"Failed to add helm repo: {e}")
                return False

        try:
            logger.info(f"Installing helm chart: {self.name}\n")
            install_args = ["helm", "install", self.name, self.chart]
            if self.set is not None:
                for key, value in self.set.items():
                    install_args.append(f"--set {key}={value}")
            if self.flags:
                install_args.extend(self.flags)
            if self.values:
                if isinstance(self.values, Path):
                    install_args.append(f"--values={str(self.values)}")
                elif isinstance(self.values, list):
                    for value in self.values:
                        install_args.append(f"--values={str(value)}")
            if self.namespace is not None:
                install_args.append(f"--namespace={self.namespace}")
                if self.create_namespace:
                    install_args.append("--create-namespace")
            run_shell_command(install_args)
            return True
        except Exception as e:
            logger.error(f"Failed to install helm chart: {e}")
        return False

    def create(self, k8s_client: K8sApiClient) -> bool:
        # Step 1: Skip resource creation if skip_create = True
        if self.skip_create:
            print_info(f"Skipping create: {self.get_resource_name()}")
            return True

        # Step 2: Check if resource is active and use_cache = True
        client: K8sApiClient = k8s_client or self.get_k8s_client()
        if self.use_cache and self.is_active(client):
            self.resource_created = True
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} already exists")
            return True

        # Step 3: Create the resource
        else:
            self.resource_created = self._create(client)
            if self.resource_created:
                print_info(f"{self.get_resource_type()}: {self.get_resource_name()} created")

        # Step 4: Run post create steps
        if self.resource_created:
            if self.save_output:
                self.save_output_file()
            logger.debug(f"Running post-create for {self.get_resource_type()}: {self.get_resource_name()}")
            return self.post_create(client)
        logger.error(f"Failed to create {self.get_resource_type()}: {self.get_resource_name()}")
        return self.resource_created

    def post_create(self, k8s_client: K8sApiClient) -> bool:
        return True

    def _update(self, k8s_client: K8sApiClient) -> Any:
        try:
            logger.info(f"Updating helm chart: {self.name}\n")
            update_args = ["helm", "upgrade", self.name, self.chart]
            if self.set is not None:
                for key, value in self.set.items():
                    update_args.append(f"--set {key}={value}")
            if self.flags:
                update_args.extend(self.flags)
            if self.values:
                if isinstance(self.values, Path):
                    update_args.append(f"--values={str(self.values)}")
            if self.namespace is not None:
                update_args.append(f"--namespace={self.namespace}")
            run_shell_command(update_args)
            return True
        except Exception as e:
            logger.error(f"Failed to update helm chart: {e}")
        return False

    def update(self, k8s_client: K8sApiClient) -> bool:
        # Step 1: Skip resource update if skip_update = True
        if self.skip_update:
            print_info(f"Skipping update: {self.get_resource_name()}")
            return True

        # Step 2: Update the resource
        client: K8sApiClient = k8s_client or self.get_k8s_client()
        if self.is_active(client):
            self.resource_updated = self._update(client)
        else:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} does not exist")
            return True

        # Step 3: Run post update steps
        if self.resource_updated:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} updated")
            if self.save_output:
                self.save_output_file()
            logger.debug(f"Running post-update for {self.get_resource_type()}: {self.get_resource_name()}")
            return self.post_update(client)
        logger.error(f"Failed to update {self.get_resource_type()}: {self.get_resource_name()}")
        return self.resource_updated

    def post_update(self, k8s_client: K8sApiClient) -> bool:
        return True

    def _delete(self, k8s_client: K8sApiClient) -> Any:
        try:
            logger.info(f"Deleting helm chart: {self.name}\n")
            delete_args = ["helm", "uninstall", self.name]
            if self.namespace is not None:
                delete_args.append(f"--namespace={self.namespace}")
            run_shell_command(delete_args)
            return True
        except Exception as e:
            logger.error(f"Failed to delete helm chart: {e}")
        return False

    def delete(self, k8s_client: K8sApiClient) -> bool:
        # Step 1: Skip resource deletion if skip_delete = True
        if self.skip_delete:
            print_info(f"Skipping delete: {self.get_resource_name()}")
            return True

        # Step 2: Delete the resource
        client: K8sApiClient = k8s_client or self.get_k8s_client()
        if self.is_active(client):
            self.resource_deleted = self._delete(client)
        else:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} does not exist")
            return True

        # Step 3: Run post delete steps
        if self.resource_deleted:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} deleted")
            if self.save_output:
                self.delete_output_file()
            logger.debug(f"Running post-delete for {self.get_resource_type()}: {self.get_resource_name()}.")
            return self.post_delete(client)
        logger.error(f"Failed to delete {self.get_resource_type()}: {self.get_resource_name()}")
        return self.resource_deleted

    def post_delete(self, k8s_client: K8sApiClient) -> bool:
        return True
