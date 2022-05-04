from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional, Type, Set, cast

from phidata.infra.k8s.args import K8sArgs
from phidata.infra.k8s.constants import (
    DEFAULT_K8S_NAMESPACE,
    DEFAULT_K8S_SERVICE_ACCOUNT,
    NAMESPACE_RESOURCE_GROUP_KEY,
    RBAC_RESOURCE_GROUP_KEY,
)
from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.exceptions import K8sArgsException
from phidata.infra.k8s.resource.base import K8sResource
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.infra.k8s.resource.kubeconfig import Kubeconfig
from phidata.infra.k8s.resource.utils import (
    filter_and_flatten_k8s_resource_groups,
    dedup_resource_types,
)
from phidata.utils.cli_console import (
    print_info,
    print_info,
    print_heading,
    print_subheading,
    print_error,
    confirm_yes_no,
)
from phidata.utils.common import is_empty
from phidata.utils.log import logger


class K8sWorker:
    """This class interacts with the Kubernetes API."""

    def __init__(self, k8s_args: K8sArgs) -> None:
        # logger.debug(f"Creating K8sWorker")
        if k8s_args is None or not isinstance(k8s_args, K8sArgs):
            raise K8sArgsException("K8sArgs invalid: {}".format(k8s_args))

        self.k8s_args: K8sArgs = k8s_args
        self.k8s_api_client: K8sApiClient = K8sApiClient(
            context=self.k8s_args.context,
            kubeconfig_path=self.k8s_args.kubeconfig_path,
        )
        self.k8s_resources: Optional[Dict[str, K8sResourceGroup]] = None
        logger.debug(f"**-+-** K8sWorker created")

    def is_client_initialized(self) -> bool:
        return self.k8s_api_client.is_initialized()

    def are_resources_initialized(self) -> bool:
        if self.k8s_resources is not None and len(self.k8s_resources) > 0:
            return True
        return False

    ######################################################
    ## Init Resources
    ######################################################

    def init_resources(self) -> None:
        """
        This function populates the self.k8s_resources dictionary.

        Step 1: Convert each PhidataApp to K8sResourceGroups.
        Step 2: Convert each CreateK8sResourceGroup to K8sResourceGroups.
        Step 3: Add all K8sResourceGroups to the self.k8s_resources dict
        """
        logger.debug("-*- Initializing K8sResourceGroups")

        # track the total number of K8sResourceGroups to build for validation
        apps_to_build = self.k8s_args.apps
        resources_to_build = self.k8s_args.resources
        create_resources_to_build = self.k8s_args.create_resources

        num_apps = len(apps_to_build) if apps_to_build is not None else 0
        num_resources = len(resources_to_build) if resources_to_build is not None else 0
        num_create_resources = (
            len(create_resources_to_build)
            if create_resources_to_build is not None
            else 0
        )
        num_rgs_to_build = num_apps + num_resources + num_create_resources
        num_rgs_built = 0

        # Step 1: Convert each PhidataApp to K8sResourceGroups.
        if apps_to_build is not None and isinstance(apps_to_build, list):
            for app in apps_to_build:
                if app.args is None:
                    print_error("Args for App {} are None".format(app))
                    continue
                logger.debug("-*- App: {}".format(app.name))

                ######################################################################
                # NOTE: VERY IMPORTANT TO GET RIGHT
                # Pass down the paths and env
                # from  WorkspaceConfig -> DockerConfig -> PhidataApp
                ######################################################################

                app.workspace_root_path = self.k8s_args.workspace_root_path
                app.workspace_config_file_path = (
                    self.k8s_args.workspace_config_file_path
                )
                app.scripts_dir = self.k8s_args.scripts_dir
                app.storage_dir = self.k8s_args.storage_dir
                app.meta_dir = self.k8s_args.meta_dir
                app.products_dir = self.k8s_args.products_dir
                app.notebooks_dir = self.k8s_args.notebooks_dir
                app.workspace_config_dir = self.k8s_args.workspace_config_dir
                app.k8s_env = self.k8s_args.k8s_env

                app_rgs: Optional[
                    Dict[str, K8sResourceGroup]
                ] = app.get_k8s_resource_groups(
                    k8s_build_context=K8sBuildContext(
                        namespace=self.k8s_args.namespace,
                        context=self.k8s_args.context,
                        service_account_name=self.k8s_args.service_account_name,
                        labels=self.k8s_args.labels,
                    )
                )
                if app_rgs is not None:
                    if self.k8s_resources is None:
                        self.k8s_resources = OrderedDict()
                    self.k8s_resources.update(app_rgs)
                    num_rgs_built += 1

        # Step 2: Convert each CreateK8sResourceGroup to K8sResourceGroups.
        if create_resources_to_build is not None and isinstance(
            create_resources_to_build, list
        ):
            for create_resource in create_resources_to_build:
                if not create_resource.enabled:
                    print_info(f"{create_resource.name} disabled")
                    continue
                logger.debug("-*- Resource: {}".format(create_resource.name))

                if isinstance(create_resource, CreateK8sResourceGroup):
                    # Create the K8sResourceGroup
                    k8s_resource_group: Optional[
                        K8sResourceGroup
                    ] = create_resource.create()
                    if k8s_resource_group is not None:
                        if self.k8s_resources is None:
                            self.k8s_resources = OrderedDict()
                        self.k8s_resources[k8s_resource_group.name] = k8s_resource_group
                    num_rgs_built += 1

        # Step 3: Add all K8sResourceGroups to the self.k8s_resources dict
        if resources_to_build is not None and isinstance(resources_to_build, list):
            for resource in resources_to_build:
                if not resource.enabled:
                    print_info(f"{resource.name} disabled")
                    continue
                logger.debug("-*- Resource: {}".format(resource.name))

                if isinstance(resource, K8sResourceGroup):
                    if self.k8s_resources is None:
                        self.k8s_resources = OrderedDict()
                    self.k8s_resources[resource.name] = resource
                    num_rgs_built += 1

        logger.debug(f"# K8sResourceGroups built: {num_rgs_built}/{num_rgs_to_build}")

    ######################################################
    ## Create Resources
    ######################################################

    def create_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        logger.debug("-*- Creating K8sResources")
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return False

        k8s_resources_to_create: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if k8s_resources_to_create is None or is_empty(k8s_resources_to_create):
            print_info("No K8sResources to create")
            return True

        # track the total number of K8sResources to create for validation
        num_resources_to_create: int = len(k8s_resources_to_create)
        num_resources_created: int = 0

        # Print the resources for validation
        print_subheading(f"Creating {num_resources_to_create} K8sResources:")
        for rsrc in k8s_resources_to_create:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        print_info(f"\n  namespace: {self.k8s_args.namespace}")
        print_info(f"  context: {self.k8s_args.context}")
        confirm = confirm_yes_no("\nConfirm deploy")
        if not confirm:
            print_info("Skipping deploy")
            return False

        for resource in k8s_resources_to_create:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_created = resource.create(k8s_client=self.k8s_api_client)
                    if _resource_created:
                        num_resources_created += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                    )
                    print_error("Error: {}".format(e))
                    print_error(
                        "Skipping resource creation, please fix and try again..."
                    )

        print_info(
            f"\n# Resources created: {num_resources_created}/{num_resources_to_create}"
        )
        if num_resources_to_create == num_resources_created:
            return True

        print_error(
            f"Resources created: {num_resources_created} do not match Resources required: {num_resources_to_create}"
        )
        return False

    def create_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.k8s_args.env
        print_subheading(
            "K8sResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return

        k8s_resources_to_create: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if k8s_resources_to_create is None or is_empty(k8s_resources_to_create):
            print_info("No K8sResources to create")
            return

        num_resources_to_create: int = len(k8s_resources_to_create)
        print_info(
            f"\n-*- Deploying this K8sConfig will create {num_resources_to_create} resources:"
        )
        print_info(f"\tnamespace: {self.k8s_args.namespace}")
        print_info(f"\tcontext: {self.k8s_args.context}")
        for resource in k8s_resources_to_create:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## Read Resources
    ######################################################

    def get_resources(self) -> Optional[Dict[str, K8sResourceGroup]]:

        logger.debug("-*- Getting K8sResources")
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return {}

        return self.k8s_resources

    def read_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Optional[List[K8sResource]]:

        logger.debug("-*- Getting K8sResources")
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return None

        k8s_resources: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
        )
        return k8s_resources

    ######################################################
    ## Delete Resources
    ######################################################

    def delete_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("-*- Deleting K8sResources")
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return False

        k8s_resources_to_delete: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="delete",
        )
        if k8s_resources_to_delete is None or is_empty(k8s_resources_to_delete):
            print_info("No K8sResources to delete")
            return True

        # track the total number of K8sResources to delete for validation
        num_resources_to_delete: int = len(k8s_resources_to_delete)
        num_resources_deleted: int = 0

        # Print the resources for validation
        # Print the resources for validation
        print_subheading(f"Deleting {num_resources_to_delete} K8sResources:")
        for rsrc in k8s_resources_to_delete:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        confirm = confirm_yes_no("\nConfirm delete")
        if not confirm:
            print_info("Skipping delete")
            return False

        for resource in k8s_resources_to_delete:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_deleted = resource.delete(k8s_client=self.k8s_api_client)
                    if _resource_deleted:
                        num_resources_deleted += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be deleted."
                    )
                    print_error(e)
                    print_error("Skipping resource deletion, please delete manually...")

        print_info(
            f"\n# Resources deleted: {num_resources_deleted}/{num_resources_to_delete}"
        )
        if num_resources_to_delete == num_resources_deleted:
            return True

        print_error(
            f"Resources deleted: {num_resources_deleted} do not match Resources required: {num_resources_to_delete}"
        )
        return False

    def delete_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.k8s_args.env
        print_subheading(
            "K8sResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return

        k8s_resources_to_delete: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="delete",
        )
        if k8s_resources_to_delete is None or is_empty(k8s_resources_to_delete):
            print_info("No K8sResources to delete")
            return

        num_resources_to_delete: int = len(k8s_resources_to_delete)
        print_info(
            f"\n-*- Shutting down this K8sConfig will delete {num_resources_to_delete} resources:"
        )
        for resource in k8s_resources_to_delete:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## Patch Resources
    ######################################################

    def patch_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("-*- Patching K8sResources")
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return False

        k8s_resources_to_patch: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if k8s_resources_to_patch is None or is_empty(k8s_resources_to_patch):
            print_info("No K8sResources to patch")
            return True

        # track the total number of K8sResources to patch for validation
        num_resources_to_patch: int = len(k8s_resources_to_patch)
        num_resources_patched: int = 0

        # Print the resources for validation
        print_subheading(f"Patching {num_resources_to_patch} K8sResources:")
        for rsrc in k8s_resources_to_patch:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        confirm = confirm_yes_no("\nConfirm patch")
        if not confirm:
            print_info("Skipping patch")
            return False

        for resource in k8s_resources_to_patch:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_patched = resource.update(k8s_client=self.k8s_api_client)
                    if _resource_patched:
                        num_resources_patched += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                    )
                    print_error(e)
                    print_error("Skipping resource, please patch manually...")

        print_info(
            f"\n# Resources patched: {num_resources_patched}/{num_resources_to_patch}"
        )
        if num_resources_to_patch == num_resources_patched:
            return True

        print_error(
            f"Resources patched: {num_resources_patched} do not match Resources required: {num_resources_to_patch}"
        )
        return False

    def patch_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.k8s_args.env
        print_subheading(
            "K8sResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.k8s_resources is None:
            self.init_resources()
            if self.k8s_resources is None:
                print_info("No Resources available")
                return

        k8s_resources_to_patch: Optional[
            List[K8sResource]
        ] = filter_and_flatten_k8s_resource_groups(
            k8s_resource_groups=self.k8s_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if k8s_resources_to_patch is None or is_empty(k8s_resources_to_patch):
            print_info("No K8sResources to patch")
            return

        num_resources_to_patch: int = len(k8s_resources_to_patch)
        print_info(
            f"\n-*- Updating this K8sConfig will patch {num_resources_to_patch} resources:"
        )
        for resource in k8s_resources_to_patch:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## End
    ######################################################

    ######################################################
    ## List Resources
    ######################################################

    # def get_active_resource_classes(
    #     self,
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    # ) -> Optional[Set[Type[K8sResource]]]:
    #     """This function scans all K8sResourceGroups under this client and
    #     returns a set of different types of K8sResource(s) as a set of classes.
    #
    #     When do we need this:
    #     Let's say your app has 1 Deployment, 1 Pod and 1 Service. You deploy it and now want
    #     to see the different types of objects running on your cluster on your cluster.
    #     To do that you need to query the API for each and every resource type to see if there are any running objects of that type.
    #     We use this function to filter & dedup the resource types this K8s client is managing.
    #     This way we don't end up scanning everything.
    #
    #     Also super useful when you want to just see Deployments running, faster responses.
    #     """
    #     if self.k8s_resources is None:
    #         logger.debug("No K8sResourceGroups available")
    #         return None
    #
    #     _filtered_k8s_resources: Optional[
    #         List[K8sResource]
    #     ] = filter_and_flatten_k8s_resource_groups(
    #         k8s_resource_groups=self.k8s_resources,
    #         type_filters=type_filters,
    #         name_filters=name_filters,
    #         sort_order="create",
    #     )
    #     return dedup_resource_types(_filtered_k8s_resources)
    #
    # def get_active_resources(
    #     self,
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    # ) -> Optional[Dict[str, List]]:
    #     """Reads the K8s Cluster and returns all active k8s_resources which satisfy the filters."""
    #
    #     from kubernetes.client.rest import ApiException
    #
    #     active_resource_classes: Optional[
    #         Set[Type[K8sResource]]
    #     ] = self.get_active_resource_classes(type_filters, name_filters)
    #
    #     if active_resource_classes is None:
    #         return None
    #
    #     _active_ns = self.get_k8s_namespace_to_use()
    #     active_k8s_objects: Dict[str, List] = defaultdict(list)
    #     for resource_class in active_resource_classes:
    #         resource_type: str = resource_class.__name__
    #         logger.debug(f"Resource Type: {resource_type}")
    #         try:
    #             _active_objects: Optional[List[Any]] = resource_class.get_from_cluster(
    #                 k8s_client=cast(K8sApiClient, self.k8s_api_client), namespace=_active_ns
    #             )
    #             if _active_objects is not None and isinstance(_active_objects, list):
    #                 active_k8s_objects[resource_type] = _active_objects
    #         except ApiException as e:
    #             logger.debug(
    #                 f"ApiException while getting {resource_type}, reason: {e.reason}"
    #             )
    #
    #     return active_k8s_objects
    #
    # def print(
    #     self,
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    #     as_yaml: Optional[bool] = True,
    # ) -> None:
    #
    #     active_k8s_objects: Optional[Dict[str, List]] = self.get_active_resources(
    #         type_filters, name_filters
    #     )
    #     if active_k8s_objects:
    #         for _r_type, active_resources in active_k8s_objects.items():
    #             print("\n{}:".format(_r_type))
    #             for _r in active_resources:
    #                 print("\t- {}".format(_r))

    ######################################################
    ## Debug
    ######################################################

    # def debug(
    #     self,
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    # ) -> None:
    #
    #     if self._k8s_client is None:
    #         logger.debug("No K8sApiClient available")
    #         return
    #     if self.k8s_resources is None:
    #         logger.debug("No K8sResourceGroups available")
    #         return
    #     _filtered_k8s_resources: Optional[
    #         List[K8sResource]
    #     ] = filter_and_flatten_k8s_resource_groups(
    #         k8s_resource_groups=self.k8s_resources,
    #         type_filters=type_filters,
    #         name_filters=name_filters,
    #         sort_order="create",
    #     )
    #     if _filtered_k8s_resources:
    #         for resource in _filtered_k8s_resources:
    #             logger.debug(f"Resource: {resource.metadata.name}")
    #             if resource and self.k8s_api_client:
    #                 resource.debug()

    ######################################################
    ## K8sApiClient
    ######################################################

    # def get_k8s_namespace_to_use(self) -> str:
    #     if self.k8s_resources is None:
    #         return DEFAULT_K8S_NAMESPACE
    #     ns_rg: K8sResourceGroup = self.k8s_resources[
    #         NAMESPACE_RESOURCE_GROUP_KEY
    #     ]
    #     if ns_rg and ns_rg.enabled and ns_rg.ns is not None:
    #         return ns_rg.ns.get_resource_name()
    #     return DEFAULT_K8S_NAMESPACE
    #
    # def get_k8s_service_account_to_use(self) -> str:
    #     if self.k8s_resources is None:
    #         return DEFAULT_K8S_SERVICE_ACCOUNT
    #     rbac_rg: K8sResourceGroup = self.k8s_resources[RBAC_RESOURCE_GROUP_KEY]
    #     if rbac_rg and rbac_rg.enabled and rbac_rg.sa is not None:
    #         return rbac_rg.sa.get_resource_name()
    #     return DEFAULT_K8S_SERVICE_ACCOUNT

    ######################################################
    ## Describe Resources
    ######################################################

    # def print_k8s_resources(
    #     self,
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    #     op_format: str = "yaml",  # yaml or json
    # ) -> None:
    #
    #     if op_format not in ("yaml", "json"):
    #         print(f"Output format {op_format} not supported")
    #         return
    #
    #     if self.k8s_resources is None:
    #         logger.debug("No K8sResourceGroups available")
    #         return
    #
    #     self.print_k8s_resource_groups(
    #         k8s_resource_groups=self.k8s_resources,
    #         type_filters=type_filters,
    #         name_filters=name_filters,
    #         as_yaml=(op_format == "yaml"),
    #     )
    #
    # @staticmethod
    # def print_k8s_resource_groups(
    #     k8s_resource_groups: Dict[str, K8sResourceGroup],
    #     type_filters: Optional[List[str]] = None,
    #     name_filters: Optional[List[str]] = None,
    #     as_yaml: Optional[bool] = True,
    # ) -> None:
    #
    #     print(
    #         "Resources: {}/{}".format(
    #             type_filters if type_filters else "*",
    #             name_filters if name_filters else "*",
    #         )
    #     )
    #     _filtered_k8s_resources: Optional[
    #         List[K8sResource]
    #     ] = filter_and_flatten_k8s_resource_groups(
    #         k8s_resource_groups=k8s_resource_groups,
    #         type_filters=type_filters,
    #         name_filters=name_filters,
    #         sort_order="create",
    #     )
    #     _resources: List[str] = []
    #     if _filtered_k8s_resources:
    #         for resource in _filtered_k8s_resources:
    #             if resource:
    #                 if as_yaml:
    #                     _yml = resource.get_k8s_manifest_yaml()
    #                     if _yml:
    #                         _resources.append(_yml)
    #                 else:
    #                     _json = resource.get_k8s_manifest_json(indent=2)
    #                     if _json:
    #                         _resources.append(_json)
    #
    #     if _resources:
    #         if as_yaml:
    #             print("---")
    #             print("---\n".join(_resources))
    #         else:
    #             print("\n".join(_resources))

    ######################################################
    ## Helpers
    ######################################################

    # def _debug_log(self, msg: Optional[str] = None) -> None:
    #     if msg:
    #         logger.debug(msg)
    #     kubeconfig_avl = True if self._kubeconfig else False
    #     k8s_client_avl = True if self.k8s_api_client else False
    #     logger.debug(f"Kubeconfig Available  : {kubeconfig_avl}")
    #     logger.debug(f"K8s_api Available  : {k8s_client_avl}")
    #
    # def verify_client(self) -> None:
    #     """Helper method to verify that we are good to perform K8s operaitons.
    #
    #     Raises:
    #         K8sClientException if something is wrong
    #     """
    #     if self._kubeconfig and self._k8s_client:
    #         pass
    #     else:
    #         self._debug_log()
    #         raise exceptions.K8sWorkerException("K8sWorker unavailable")
