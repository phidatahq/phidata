from typing import List, Optional, Dict, Any, Union

from pydantic import Field, field_validator, FieldValidationInfo

from phi.k8s.app.base import K8sApp
from phi.k8s.app.context import K8sBuildContext
from phi.k8s.api_client import K8sApiClient
from phi.k8s.create.base import CreateK8sResource
from phi.k8s.resource.base import K8sResource
from phi.infra.resource.group import InfraResourceGroup
from phi.workspace.settings import WorkspaceSettings
from phi.utils.log import logger


class K8sResourceGroup(InfraResourceGroup):
    apps: Optional[List[K8sApp]] = None
    resources: Optional[List[Union[K8sResource, CreateK8sResource]]] = None

    # K8s namespace to use
    namespace: str = "default"
    # K8s context to use
    context: Optional[str] = Field(None, validate_default=True)
    # Service account to use
    service_account_name: Optional[str] = None
    # Common labels to add to all resources
    common_labels: Optional[Dict[str, str]] = None
    # Path to kubeconfig file
    kubeconfig: Optional[str] = Field(None, validate_default=True)
    # Get context and kubeconfig from an EksCluster
    eks_cluster: Optional[Any] = None

    # -*- Cached Data
    _api_client: Optional[K8sApiClient] = None

    @property
    def k8s_client(self) -> K8sApiClient:
        if self._api_client is None:
            self._api_client = K8sApiClient(context=self.context, kubeconfig_path=self.kubeconfig)
        return self._api_client

    @field_validator("context", mode="before")
    def update_context(cls, context, info: FieldValidationInfo):
        if context is not None:
            return context

        # If context is not provided, then get it from eks_cluster
        eks_cluster = info.data.get("eks_cluster", None)
        if eks_cluster is not None:
            from phi.aws.resource.eks.cluster import EksCluster

            if not isinstance(eks_cluster, EksCluster):
                raise TypeError("eks_cluster not of type EksCluster")
            return eks_cluster.get_kubeconfig_context_name()
        return context

    @field_validator("kubeconfig", mode="before")
    def update_kubeconfig(cls, kubeconfig, info: FieldValidationInfo):
        if kubeconfig is not None:
            return kubeconfig

        # If kubeconfig is not provided, then get it from eks_cluster
        eks_cluster = info.data.get("eks_cluster", None)
        if eks_cluster is not None:
            from phi.aws.resource.eks.cluster import EksCluster

            if not isinstance(eks_cluster, EksCluster):
                raise TypeError("eks_cluster not of type EksCluster")
            return eks_cluster.kubeconfig_path
        return kubeconfig

    def create_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        force: Optional[bool] = None,
        workspace_settings: Optional[WorkspaceSettings] = None,
    ) -> int:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Creating K8sResources")
        # Build a list of K8sResources to create
        resources_to_create: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, K8sResource) and r.should_create(
                    group_filter=group_filter,
                    name_filter=name_filter,
                    type_filter=type_filter,
                ):
                    r.set_workspace_settings(workspace_settings=workspace_settings)
                    resources_to_create.append(r)
                if isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None and _k8s_resource.should_create(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        _k8s_resource.set_workspace_settings(workspace_settings=workspace_settings)
                        resources_to_create.append(_k8s_resource)

        # Build a list of K8sApps to create
        apps_to_create: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if app.should_create(group_filter=group_filter):
                    apps_to_create.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_create) > 0:
            logger.debug(f"Found {len(apps_to_create)} apps to create")
            for app in apps_to_create:
                app.set_workspace_settings(workspace_settings=workspace_settings)
                app_resources = app.get_resources(build_context=K8sBuildContext())
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_create(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_create.append(app_resource)

        # Sort the K8sResources in install order
        resources_to_create.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000))

        # Deduplicate K8sResources
        deduped_resources_to_create: List[K8sResource] = []
        for r in resources_to_create:
            if r not in deduped_resources_to_create:
                deduped_resources_to_create.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[K8sResource] = []
        logger.debug("-*- Building K8sResources dependency graph")
        for k8s_resource in deduped_resources_to_create:
            # Logic to follow if resource has dependencies
            if k8s_resource.depends_on is not None:
                # Add the dependencies before the resource itself
                for dep in k8s_resource.depends_on:
                    if isinstance(dep, K8sResource):
                        if dep not in final_k8s_resources:
                            logger.debug(f"-*- Adding {dep.name}, dependency of {k8s_resource.name}")
                            final_k8s_resources.append(dep)

                # Add the resource to be created after its dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)
            else:
                # Add the resource to be created if it has no dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

        # Track the total number of K8sResources to create for validation
        num_resources_to_create: int = len(final_k8s_resources)
        num_resources_created: int = 0
        if num_resources_to_create == 0:
            print_info("No K8sResources to create")
            return 0

        if dry_run:
            print_heading("--**- K8s resources to create:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_create} resources")
            return 0

        # Validate resources to be created
        if not auto_confirm:
            print_heading("--**-- Confirm resources to create:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_create} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping deploy")
                print_info("-*-")
                return 0

        for resource in final_k8s_resources:
            print_info(f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}")
            if force is True:
                resource.force = True
            # logger.debug(resource)
            try:
                _resource_created = resource.create(k8s_client=self.k8s_client)
                if _resource_created:
                    num_resources_created += 1
                else:
                    if workspace_settings is not None and not workspace_settings.continue_on_create_failure:
                        return num_resources_created
            except Exception as e:
                logger.error(f"Failed to create {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.error(e)
                logger.error("Please fix and try again...")

        print_info(f"\n# Resources created: {num_resources_created}/{num_resources_to_create}")
        if num_resources_to_create != num_resources_created:
            logger.error(
                f"Resources created: {num_resources_created} do not match resources required: {num_resources_to_create}"
            )  # noqa: E501
        return num_resources_created

    def delete_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        force: Optional[bool] = None,
        workspace_settings: Optional[WorkspaceSettings] = None,
    ) -> int:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Deleting K8sResources")
        # Build a list of K8sResources to delete
        resources_to_delete: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, K8sResource) and r.should_delete(
                    group_filter=group_filter,
                    name_filter=name_filter,
                    type_filter=type_filter,
                ):
                    r.set_workspace_settings(workspace_settings=workspace_settings)
                    resources_to_delete.append(r)
                if isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None and _k8s_resource.should_delete(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        _k8s_resource.set_workspace_settings(workspace_settings=workspace_settings)
                        resources_to_delete.append(_k8s_resource)

        # Build a list of K8sApps to delete
        apps_to_delete: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if app.should_delete(group_filter=group_filter):
                    apps_to_delete.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_delete) > 0:
            logger.debug(f"Found {len(apps_to_delete)} apps to delete")
            for app in apps_to_delete:
                app.set_workspace_settings(workspace_settings=workspace_settings)
                app_resources = app.get_resources(build_context=K8sBuildContext())
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_delete(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_delete.append(app_resource)

        # Sort the K8sResources in install order
        resources_to_delete.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000), reverse=True)

        # Deduplicate K8sResources
        deduped_resources_to_delete: List[K8sResource] = []
        for r in resources_to_delete:
            if r not in deduped_resources_to_delete:
                deduped_resources_to_delete.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[K8sResource] = []
        logger.debug("-*- Building K8sResources dependency graph")
        for k8s_resource in deduped_resources_to_delete:
            # Logic to follow if resource has dependencies
            if k8s_resource.depends_on is not None:
                # 1. Reverse the order of dependencies
                k8s_resource.depends_on.reverse()

                # 2. Remove the dependencies if they are already added to the final_k8s_resources
                for dep in k8s_resource.depends_on:
                    if dep in final_k8s_resources:
                        logger.debug(f"-*- Removing {dep.name}, dependency of {k8s_resource.name}")
                        final_k8s_resources.remove(dep)

                # 3. Add the resource to be deleted before its dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

                # 4. Add the dependencies back in reverse order
                for dep in k8s_resource.depends_on:
                    if isinstance(dep, K8sResource):
                        if dep not in final_k8s_resources:
                            logger.debug(f"-*- Adding {dep.name}, dependency of {k8s_resource.name}")
                            final_k8s_resources.append(dep)
            else:
                # Add the resource to be deleted if it has no dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

        # Track the total number of K8sResources to delete for validation
        num_resources_to_delete: int = len(final_k8s_resources)
        num_resources_deleted: int = 0
        if num_resources_to_delete == 0:
            print_info("No K8sResources to delete")
            return 0

        if dry_run:
            print_heading("--**- K8s resources to delete:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_delete} resources")
            return 0

        # Validate resources to be deleted
        if not auto_confirm:
            print_heading("--**-- Confirm resources to delete:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_delete} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping delete")
                print_info("-*-")
                return 0

        for resource in final_k8s_resources:
            print_info(f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}")
            if force is True:
                resource.force = True
            # logger.debug(resource)
            try:
                _resource_deleted = resource.delete(k8s_client=self.k8s_client)
                if _resource_deleted:
                    num_resources_deleted += 1
                else:
                    if workspace_settings is not None and not workspace_settings.continue_on_delete_failure:
                        return num_resources_deleted
            except Exception as e:
                logger.error(f"Failed to delete {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.error(e)
                logger.error("Please fix and try again...")

        print_info(f"\n# Resources deleted: {num_resources_deleted}/{num_resources_to_delete}")
        if num_resources_to_delete != num_resources_deleted:
            logger.error(
                f"Resources deleted: {num_resources_deleted} do not match resources required: {num_resources_to_delete}"
            )  # noqa: E501
        return num_resources_deleted

    def update_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        force: Optional[bool] = None,
        workspace_settings: Optional[WorkspaceSettings] = None,
    ) -> int:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Updating K8sResources")

        # Build a list of K8sResources to update
        resources_to_update: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, K8sResource) and r.should_update(
                    group_filter=group_filter,
                    name_filter=name_filter,
                    type_filter=type_filter,
                ):
                    r.set_workspace_settings(workspace_settings=workspace_settings)
                    resources_to_update.append(r)
                if isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None and _k8s_resource.should_update(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        _k8s_resource.set_workspace_settings(workspace_settings=workspace_settings)
                        resources_to_update.append(_k8s_resource)

        # Build a list of K8sApps to update
        apps_to_update: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if app.should_update(group_filter=group_filter):
                    apps_to_update.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_update) > 0:
            logger.debug(f"Found {len(apps_to_update)} apps to update")
            for app in apps_to_update:
                app.set_workspace_settings(workspace_settings=workspace_settings)
                app_resources = app.get_resources(build_context=K8sBuildContext())
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_update(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_update.append(app_resource)

        # Sort the K8sResources in install order
        resources_to_update.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000), reverse=True)

        # Deduplicate K8sResources
        deduped_resources_to_update: List[K8sResource] = []
        for r in resources_to_update:
            if r not in deduped_resources_to_update:
                deduped_resources_to_update.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[K8sResource] = []
        logger.debug("-*- Building K8sResources dependency graph")
        for k8s_resource in deduped_resources_to_update:
            # Logic to follow if resource has dependencies
            if k8s_resource.depends_on is not None:
                # 1. Reverse the order of dependencies
                k8s_resource.depends_on.reverse()

                # 2. Remove the dependencies if they are already added to the final_k8s_resources
                for dep in k8s_resource.depends_on:
                    if dep in final_k8s_resources:
                        logger.debug(f"-*- Removing {dep.name}, dependency of {k8s_resource.name}")
                        final_k8s_resources.remove(dep)

                # 3. Add the resource to be updated before its dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

                # 4. Add the dependencies back in reverse order
                for dep in k8s_resource.depends_on:
                    if isinstance(dep, K8sResource):
                        if dep not in final_k8s_resources:
                            logger.debug(f"-*- Adding {dep.name}, dependency of {k8s_resource.name}")
                            final_k8s_resources.append(dep)
            else:
                # Add the resource to be updated if it has no dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

        # Track the total number of K8sResources to update for validation
        num_resources_to_update: int = len(final_k8s_resources)
        num_resources_updated: int = 0
        if num_resources_to_update == 0:
            print_info("No K8sResources to update")
            return 0

        if dry_run:
            print_heading("--**- K8s resources to update:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_update} resources")
            return 0

        # Validate resources to be updated
        if not auto_confirm:
            print_heading("--**-- Confirm resources to update:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_update} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping patch")
                print_info("-*-")
                return 0

        for resource in final_k8s_resources:
            print_info(f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}")
            if force is True:
                resource.force = True
            # logger.debug(resource)
            try:
                _resource_updated = resource.update(k8s_client=self.k8s_client)
                if _resource_updated:
                    num_resources_updated += 1
                else:
                    if workspace_settings is not None and not workspace_settings.continue_on_patch_failure:
                        return num_resources_updated
            except Exception as e:
                logger.error(f"Failed to update {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.error(e)
                logger.error("Please fix and try again...")

        print_info(f"\n# Resources updated: {num_resources_updated}/{num_resources_to_update}")
        if num_resources_to_update != num_resources_updated:
            logger.error(
                f"Resources updated: {num_resources_updated} do not match resources required: {num_resources_to_update}"
            )  # noqa: E501
        return num_resources_updated
