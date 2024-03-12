from typing import List, Optional, Dict, Any, Union, Tuple

from pydantic import Field, field_validator, ValidationInfo

from phi.app.group import AppGroup
from phi.resource.group import ResourceGroup
from phi.k8s.app.base import K8sApp
from phi.k8s.app.context import K8sBuildContext
from phi.k8s.api_client import K8sApiClient
from phi.k8s.create.base import CreateK8sResource
from phi.k8s.resource.base import K8sResource
from phi.k8s.helm.chart import HelmChart
from phi.infra.resources import InfraResources
from phi.utils.log import logger


class K8sResources(InfraResources):
    apps: Optional[List[Union[K8sApp, AppGroup]]] = None
    resources: Optional[List[Union[K8sResource, CreateK8sResource, ResourceGroup]]] = None
    charts: Optional[List[HelmChart]] = None

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
    def update_context(cls, context, info: ValidationInfo):
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
    def update_kubeconfig(cls, kubeconfig, info: ValidationInfo):
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
        pull: Optional[bool] = None,
    ) -> Tuple[int, int]:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Creating K8sResources")
        # Build a list of K8sResources to create
        resources_to_create: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, ResourceGroup):
                    resources_from_resource_group = r.get_resources()
                    if len(resources_from_resource_group) > 0:
                        for resource_from_resource_group in resources_from_resource_group:
                            if isinstance(resource_from_resource_group, K8sResource):
                                resource_from_resource_group.set_workspace_settings(
                                    workspace_settings=self.workspace_settings
                                )
                                if resource_from_resource_group.group is None and self.name is not None:
                                    resource_from_resource_group.group = self.name
                                if resource_from_resource_group.should_create(
                                    group_filter=group_filter,
                                    name_filter=name_filter,
                                    type_filter=type_filter,
                                ):
                                    resources_to_create.append(resource_from_resource_group)
                            elif isinstance(resource_from_resource_group, CreateK8sResource):
                                _k8s_resource = resource_from_resource_group.create()
                                if _k8s_resource is not None:
                                    _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                                    if _k8s_resource.group is None and self.name is not None:
                                        _k8s_resource.group = self.name
                                    if _k8s_resource.should_create(
                                        group_filter=group_filter,
                                        name_filter=name_filter,
                                        type_filter=type_filter,
                                    ):
                                        resources_to_create.append(_k8s_resource)
                elif isinstance(r, K8sResource):
                    r.set_workspace_settings(workspace_settings=self.workspace_settings)
                    if r.group is None and self.name is not None:
                        r.group = self.name
                    if r.should_create(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        resources_to_create.append(r)
                elif isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None:
                        _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if _k8s_resource.group is None and self.name is not None:
                            _k8s_resource.group = self.name
                        if _k8s_resource.should_create(
                            group_filter=group_filter,
                            name_filter=name_filter,
                            type_filter=type_filter,
                        ):
                            resources_to_create.append(_k8s_resource)

        # Build a list of K8sApps to create
        apps_to_create: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if isinstance(app, AppGroup):
                    apps_from_app_group = app.get_apps()
                    if len(apps_from_app_group) > 0:
                        for app_from_app_group in apps_from_app_group:
                            if isinstance(app_from_app_group, K8sApp):
                                if app_from_app_group.group is None and self.name is not None:
                                    app_from_app_group.group = self.name
                                if app_from_app_group.should_create(group_filter=group_filter):
                                    apps_to_create.append(app_from_app_group)
                elif isinstance(app, K8sApp):
                    if app.group is None and self.name is not None:
                        app.group = self.name
                    if app.should_create(group_filter=group_filter):
                        apps_to_create.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_create) > 0:
            logger.debug(f"Found {len(apps_to_create)} apps to create")
            for app in apps_to_create:
                app.set_workspace_settings(workspace_settings=self.workspace_settings)
                app_resources = app.get_resources(
                    build_context=K8sBuildContext(
                        namespace=self.namespace,
                        context=self.context,
                        service_account_name=self.service_account_name,
                        labels=self.common_labels,
                    )
                )
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_create(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_create.append(app_resource)
                        elif isinstance(app_resource, CreateK8sResource):
                            _k8s_resource = app_resource.create()
                            if _k8s_resource is not None and _k8s_resource.should_create(
                                group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                            ):
                                resources_to_create.append(_k8s_resource)

        # Sort the K8sResources in install order
        resources_to_create.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000))

        # Deduplicate K8sResources
        deduped_resources_to_create: List[K8sResource] = []
        for r in resources_to_create:
            if r not in deduped_resources_to_create:
                deduped_resources_to_create.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[Union[K8sResource, HelmChart]] = []
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

        # Build a list of HelmCharts to create
        if self.charts is not None:
            for chart in self.charts:
                if chart.group is None and self.name is not None:
                    chart.group = self.name
                if chart.should_create(group_filter=group_filter):
                    if chart not in final_k8s_resources:
                        chart.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if chart.namespace is None:
                            chart.namespace = self.namespace
                        final_k8s_resources.append(chart)

        # Track the total number of K8sResources to create for validation
        num_resources_to_create: int = len(final_k8s_resources)
        num_resources_created: int = 0
        if num_resources_to_create == 0:
            return 0, 0

        if dry_run:
            print_heading("--**- K8s resources to create:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_create} resources")
            return 0, 0

        # Validate resources to be created
        if not auto_confirm:
            print_heading("\n--**-- Confirm resources to create:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_create} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping deploy")
                print_info("-*-")
                return 0, 0

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
                    if self.workspace_settings is not None and not self.workspace_settings.continue_on_create_failure:
                        return num_resources_created, num_resources_to_create
            except Exception as e:
                logger.error(f"Failed to create {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.exception(e)
                logger.error("Please fix and try again...")

        print_heading(f"\n--**-- Resources created: {num_resources_created}/{num_resources_to_create}")
        if num_resources_to_create != num_resources_created:
            logger.error(
                f"Resources created: {num_resources_created} do not match resources required: {num_resources_to_create}"
            )  # noqa: E501
        return num_resources_created, num_resources_to_create

    def delete_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        force: Optional[bool] = None,
    ) -> Tuple[int, int]:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Deleting K8sResources")
        # Build a list of K8sResources to delete
        resources_to_delete: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, ResourceGroup):
                    resources_from_resource_group = r.get_resources()
                    if len(resources_from_resource_group) > 0:
                        for resource_from_resource_group in resources_from_resource_group:
                            if isinstance(resource_from_resource_group, K8sResource):
                                resource_from_resource_group.set_workspace_settings(
                                    workspace_settings=self.workspace_settings
                                )
                                if resource_from_resource_group.group is None and self.name is not None:
                                    resource_from_resource_group.group = self.name
                                if resource_from_resource_group.should_delete(
                                    group_filter=group_filter,
                                    name_filter=name_filter,
                                    type_filter=type_filter,
                                ):
                                    resources_to_delete.append(resource_from_resource_group)
                            elif isinstance(resource_from_resource_group, CreateK8sResource):
                                _k8s_resource = resource_from_resource_group.create()
                                if _k8s_resource is not None:
                                    _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                                    if _k8s_resource.group is None and self.name is not None:
                                        _k8s_resource.group = self.name
                                    if _k8s_resource.should_delete(
                                        group_filter=group_filter,
                                        name_filter=name_filter,
                                        type_filter=type_filter,
                                    ):
                                        resources_to_delete.append(_k8s_resource)
                elif isinstance(r, K8sResource):
                    r.set_workspace_settings(workspace_settings=self.workspace_settings)
                    if r.group is None and self.name is not None:
                        r.group = self.name
                    if r.should_delete(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        resources_to_delete.append(r)
                elif isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None:
                        _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if _k8s_resource.group is None and self.name is not None:
                            _k8s_resource.group = self.name
                        if _k8s_resource.should_delete(
                            group_filter=group_filter,
                            name_filter=name_filter,
                            type_filter=type_filter,
                        ):
                            resources_to_delete.append(_k8s_resource)

        # Build a list of K8sApps to delete
        apps_to_delete: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if isinstance(app, AppGroup):
                    apps_from_app_group = app.get_apps()
                    if len(apps_from_app_group) > 0:
                        for app_from_app_group in apps_from_app_group:
                            if isinstance(app_from_app_group, K8sApp):
                                if app_from_app_group.group is None and self.name is not None:
                                    app_from_app_group.group = self.name
                                if app_from_app_group.should_delete(group_filter=group_filter):
                                    apps_to_delete.append(app_from_app_group)
                elif isinstance(app, K8sApp):
                    if app.group is None and self.name is not None:
                        app.group = self.name
                    if app.should_delete(group_filter=group_filter):
                        apps_to_delete.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_delete) > 0:
            logger.debug(f"Found {len(apps_to_delete)} apps to delete")
            for app in apps_to_delete:
                app.set_workspace_settings(workspace_settings=self.workspace_settings)
                app_resources = app.get_resources(
                    build_context=K8sBuildContext(
                        namespace=self.namespace,
                        context=self.context,
                        service_account_name=self.service_account_name,
                        labels=self.common_labels,
                    )
                )
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_delete(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_delete.append(app_resource)
                        elif isinstance(app_resource, CreateK8sResource):
                            _k8s_resource = app_resource.create()
                            if _k8s_resource is not None and _k8s_resource.should_delete(
                                group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                            ):
                                resources_to_delete.append(_k8s_resource)

        # Sort the K8sResources in install order
        resources_to_delete.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000), reverse=True)

        # Deduplicate K8sResources
        deduped_resources_to_delete: List[K8sResource] = []
        for r in resources_to_delete:
            if r not in deduped_resources_to_delete:
                deduped_resources_to_delete.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[Union[K8sResource, HelmChart]] = []
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

        # Build a list of HelmCharts to create
        if self.charts is not None:
            for chart in self.charts:
                if chart.group is None and self.name is not None:
                    chart.group = self.name
                if chart.should_create(group_filter=group_filter):
                    if chart not in final_k8s_resources:
                        chart.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if chart.namespace is None:
                            chart.namespace = self.namespace
                        final_k8s_resources.append(chart)

        # Track the total number of K8sResources to delete for validation
        num_resources_to_delete: int = len(final_k8s_resources)
        num_resources_deleted: int = 0
        if num_resources_to_delete == 0:
            return 0, 0

        if dry_run:
            print_heading("--**- K8s resources to delete:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_delete} resources")
            return 0, 0

        # Validate resources to be deleted
        if not auto_confirm:
            print_heading("\n--**-- Confirm resources to delete:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_delete} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping delete")
                print_info("-*-")
                return 0, 0

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
                    if self.workspace_settings is not None and not self.workspace_settings.continue_on_delete_failure:
                        return num_resources_deleted, num_resources_to_delete
            except Exception as e:
                logger.error(f"Failed to delete {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.exception(e)
                logger.error("Please fix and try again...")

        print_heading(f"\n--**-- Resources deleted: {num_resources_deleted}/{num_resources_to_delete}")
        if num_resources_to_delete != num_resources_deleted:
            logger.error(
                f"Resources deleted: {num_resources_deleted} do not match resources required: {num_resources_to_delete}"
            )  # noqa: E501
        return num_resources_deleted, num_resources_to_delete

    def update_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        force: Optional[bool] = None,
        pull: Optional[bool] = None,
    ) -> Tuple[int, int]:
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Updating K8sResources")

        # Build a list of K8sResources to update
        resources_to_update: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, ResourceGroup):
                    resources_from_resource_group = r.get_resources()
                    if len(resources_from_resource_group) > 0:
                        for resource_from_resource_group in resources_from_resource_group:
                            if isinstance(resource_from_resource_group, K8sResource):
                                resource_from_resource_group.set_workspace_settings(
                                    workspace_settings=self.workspace_settings
                                )
                                if resource_from_resource_group.group is None and self.name is not None:
                                    resource_from_resource_group.group = self.name
                                if resource_from_resource_group.should_update(
                                    group_filter=group_filter,
                                    name_filter=name_filter,
                                    type_filter=type_filter,
                                ):
                                    resources_to_update.append(resource_from_resource_group)
                            elif isinstance(resource_from_resource_group, CreateK8sResource):
                                _k8s_resource = resource_from_resource_group.create()
                                if _k8s_resource is not None:
                                    _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                                    if _k8s_resource.group is None and self.name is not None:
                                        _k8s_resource.group = self.name
                                    if _k8s_resource.should_update(
                                        group_filter=group_filter,
                                        name_filter=name_filter,
                                        type_filter=type_filter,
                                    ):
                                        resources_to_update.append(_k8s_resource)
                elif isinstance(r, K8sResource):
                    r.set_workspace_settings(workspace_settings=self.workspace_settings)
                    if r.group is None and self.name is not None:
                        r.group = self.name
                    if r.should_update(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        resources_to_update.append(r)
                elif isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None:
                        _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if _k8s_resource.group is None and self.name is not None:
                            _k8s_resource.group = self.name
                        if _k8s_resource.should_update(
                            group_filter=group_filter,
                            name_filter=name_filter,
                            type_filter=type_filter,
                        ):
                            resources_to_update.append(_k8s_resource)

        # Build a list of K8sApps to update
        apps_to_update: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if isinstance(app, AppGroup):
                    apps_from_app_group = app.get_apps()
                    if len(apps_from_app_group) > 0:
                        for app_from_app_group in apps_from_app_group:
                            if isinstance(app_from_app_group, K8sApp):
                                if app_from_app_group.group is None and self.name is not None:
                                    app_from_app_group.group = self.name
                                if app_from_app_group.should_update(group_filter=group_filter):
                                    apps_to_update.append(app_from_app_group)
                elif isinstance(app, K8sApp):
                    if app.group is None and self.name is not None:
                        app.group = self.name
                    if app.should_update(group_filter=group_filter):
                        apps_to_update.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_update) > 0:
            logger.debug(f"Found {len(apps_to_update)} apps to update")
            for app in apps_to_update:
                app.set_workspace_settings(workspace_settings=self.workspace_settings)
                app_resources = app.get_resources(
                    build_context=K8sBuildContext(
                        namespace=self.namespace,
                        context=self.context,
                        service_account_name=self.service_account_name,
                        labels=self.common_labels,
                    )
                )
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_update(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_update.append(app_resource)
                        elif isinstance(app_resource, CreateK8sResource):
                            _k8s_resource = app_resource.create()
                            if _k8s_resource is not None and _k8s_resource.should_update(
                                group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                            ):
                                resources_to_update.append(_k8s_resource)

        # Sort the K8sResources in install order
        resources_to_update.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000), reverse=True)

        # Deduplicate K8sResources
        deduped_resources_to_update: List[K8sResource] = []
        for r in resources_to_update:
            if r not in deduped_resources_to_update:
                deduped_resources_to_update.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[Union[K8sResource, HelmChart]] = []
        logger.debug("-*- Building K8sResources dependency graph")
        for k8s_resource in deduped_resources_to_update:
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

        # Build a list of HelmCharts to create
        if self.charts is not None:
            for chart in self.charts:
                if chart.group is None and self.name is not None:
                    chart.group = self.name
                if chart.should_create(group_filter=group_filter):
                    if chart not in final_k8s_resources:
                        chart.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if chart.namespace is None:
                            chart.namespace = self.namespace
                        final_k8s_resources.append(chart)

        # Track the total number of K8sResources to update for validation
        num_resources_to_update: int = len(final_k8s_resources)
        num_resources_updated: int = 0
        if num_resources_to_update == 0:
            return 0, 0

        if dry_run:
            print_heading("--**- K8s resources to update:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_update} resources")
            return 0, 0

        # Validate resources to be updated
        if not auto_confirm:
            print_heading("\n--**-- Confirm resources to update:")
            for resource in final_k8s_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info("")
            print_info(f"Total {num_resources_to_update} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping patch")
                print_info("-*-")
                return 0, 0

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
                    if self.workspace_settings is not None and not self.workspace_settings.continue_on_patch_failure:
                        return num_resources_updated, num_resources_to_update
            except Exception as e:
                logger.error(f"Failed to update {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.exception(e)
                logger.error("Please fix and try again...")

        print_heading(f"\n--**-- Resources updated: {num_resources_updated}/{num_resources_to_update}")
        if num_resources_to_update != num_resources_updated:
            logger.error(
                f"Resources updated: {num_resources_updated} do not match resources required: {num_resources_to_update}"
            )  # noqa: E501
        return num_resources_updated, num_resources_to_update

    def save_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Tuple[int, int]:
        from phi.cli.console import print_info, print_heading
        from phi.k8s.resource.types import K8sResourceInstallOrder

        logger.debug("-*- Saving K8sResources")

        # Build a list of K8sResources to save
        resources_to_save: List[K8sResource] = []
        if self.resources is not None:
            for r in self.resources:
                if isinstance(r, ResourceGroup):
                    resources_from_resource_group = r.get_resources()
                    if len(resources_from_resource_group) > 0:
                        for resource_from_resource_group in resources_from_resource_group:
                            if isinstance(resource_from_resource_group, K8sResource):
                                resource_from_resource_group.env = self.env
                                resource_from_resource_group.set_workspace_settings(
                                    workspace_settings=self.workspace_settings
                                )
                                if resource_from_resource_group.group is None and self.name is not None:
                                    resource_from_resource_group.group = self.name
                                if resource_from_resource_group.should_create(
                                    group_filter=group_filter,
                                    name_filter=name_filter,
                                    type_filter=type_filter,
                                ):
                                    resources_to_save.append(resource_from_resource_group)
                            elif isinstance(resource_from_resource_group, CreateK8sResource):
                                _k8s_resource = resource_from_resource_group.save()
                                if _k8s_resource is not None:
                                    _k8s_resource.env = self.env
                                    _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                                    if _k8s_resource.group is None and self.name is not None:
                                        _k8s_resource.group = self.name
                                    if _k8s_resource.should_create(
                                        group_filter=group_filter,
                                        name_filter=name_filter,
                                        type_filter=type_filter,
                                    ):
                                        resources_to_save.append(_k8s_resource)
                elif isinstance(r, K8sResource):
                    r.env = self.env
                    r.set_workspace_settings(workspace_settings=self.workspace_settings)
                    if r.group is None and self.name is not None:
                        r.group = self.name
                    if r.should_create(
                        group_filter=group_filter,
                        name_filter=name_filter,
                        type_filter=type_filter,
                    ):
                        resources_to_save.append(r)
                elif isinstance(r, CreateK8sResource):
                    _k8s_resource = r.create()
                    if _k8s_resource is not None:
                        _k8s_resource.env = self.env
                        _k8s_resource.set_workspace_settings(workspace_settings=self.workspace_settings)
                        if _k8s_resource.group is None and self.name is not None:
                            _k8s_resource.group = self.name
                        if _k8s_resource.should_create(
                            group_filter=group_filter,
                            name_filter=name_filter,
                            type_filter=type_filter,
                        ):
                            resources_to_save.append(_k8s_resource)

        # Build a list of K8sApps to save
        apps_to_save: List[K8sApp] = []
        if self.apps is not None:
            for app in self.apps:
                if isinstance(app, AppGroup):
                    apps_from_app_group = app.get_apps()
                    if len(apps_from_app_group) > 0:
                        for app_from_app_group in apps_from_app_group:
                            if isinstance(app_from_app_group, K8sApp):
                                if app_from_app_group.group is None and self.name is not None:
                                    app_from_app_group.group = self.name
                                if app_from_app_group.should_create(group_filter=group_filter):
                                    apps_to_save.append(app_from_app_group)
                elif isinstance(app, K8sApp):
                    if app.group is None and self.name is not None:
                        app.group = self.name
                    if app.should_create(group_filter=group_filter):
                        apps_to_save.append(app)

        # Get the list of K8sResources from the K8sApps
        if len(apps_to_save) > 0:
            logger.debug(f"Found {len(apps_to_save)} apps to save")
            for app in apps_to_save:
                app.set_workspace_settings(workspace_settings=self.workspace_settings)
                app_resources = app.get_resources(
                    build_context=K8sBuildContext(
                        namespace=self.namespace,
                        context=self.context,
                        service_account_name=self.service_account_name,
                        labels=self.common_labels,
                    )
                )
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, K8sResource) and app_resource.should_create(
                            group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_save.append(app_resource)
                        elif isinstance(app_resource, CreateK8sResource):
                            _k8s_resource = app_resource.save()
                            if _k8s_resource is not None and _k8s_resource.should_create(
                                group_filter=group_filter, name_filter=name_filter, type_filter=type_filter
                            ):
                                resources_to_save.append(_k8s_resource)

        # Sort the K8sResources in install order
        resources_to_save.sort(key=lambda x: K8sResourceInstallOrder.get(x.__class__.__name__, 5000))

        # Deduplicate K8sResources
        deduped_resources_to_save: List[K8sResource] = []
        for r in resources_to_save:
            if r not in deduped_resources_to_save:
                deduped_resources_to_save.append(r)

        # Implement dependency sorting
        final_k8s_resources: List[K8sResource] = []
        logger.debug("-*- Building K8sResources dependency graph")
        for k8s_resource in deduped_resources_to_save:
            # Logic to follow if resource has dependencies
            if k8s_resource.depends_on is not None:
                # Add the dependencies before the resource itself
                for dep in k8s_resource.depends_on:
                    if isinstance(dep, K8sResource):
                        if dep not in final_k8s_resources:
                            logger.debug(f"-*- Adding {dep.name}, dependency of {k8s_resource.name}")
                            final_k8s_resources.append(dep)

                # Add the resource to be saved after its dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)
            else:
                # Add the resource to be saved if it has no dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"-*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

        # Track the total number of K8sResources to save for validation
        num_resources_to_save: int = len(final_k8s_resources)
        num_resources_saved: int = 0
        if num_resources_to_save == 0:
            return 0, 0

        for resource in final_k8s_resources:
            print_info(f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}")
            try:
                _resource_path = resource.save_manifests(default_flow_style=False)
                if _resource_path is not None:
                    print_info(f"Saved to: {_resource_path}")
                    num_resources_saved += 1
            except Exception as e:
                logger.error(f"Failed to save {resource.get_resource_type()}: {resource.get_resource_name()}")
                logger.exception(e)
                logger.error("Please fix and try again...")

        print_heading(f"\n--**-- Resources saved: {num_resources_saved}/{num_resources_to_save}")
        if num_resources_to_save != num_resources_saved:
            logger.error(
                f"Resources saved: {num_resources_saved} do not match resources required: {num_resources_to_save}"
            )  # noqa: E501
        return num_resources_saved, num_resources_to_save
