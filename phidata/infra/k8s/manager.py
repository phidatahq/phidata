from pathlib import Path
from typing import Optional, List, Dict

from phidata.infra.k8s.args import K8sArgs
from phidata.infra.k8s.enums.manager_status import K8sManagerStatus
from phidata.infra.k8s.exceptions import K8sArgsException
from phidata.infra.k8s.resource.base import K8sResource
from phidata.infra.k8s.resource.group import K8sResourceGroup
from phidata.infra.k8s.worker import K8sWorker
from phidata.utils.log import logger


class K8sManager:
    def __init__(self, k8s_args: K8sArgs):
        if k8s_args is None or not isinstance(k8s_args, K8sArgs):
            raise K8sArgsException("Invalid K8sArgs")
        if k8s_args.workspace_root_path is None or not isinstance(
            k8s_args.workspace_root_path, Path
        ):
            raise K8sArgsException("workspace_root_path invalid")
        if k8s_args.workspace_config_file_path is None or not isinstance(
            k8s_args.workspace_config_file_path, Path
        ):
            raise K8sArgsException("workspace_config_file_path invalid")

        self.k8s_args: K8sArgs = k8s_args
        self.k8s_worker: K8sWorker = K8sWorker(self.k8s_args)
        self.k8s_status: K8sManagerStatus = K8sManagerStatus.PRE_INIT
        logger.debug("**-+-** K8sManager created")

    def get_status(self, refresh: bool = False) -> K8sManagerStatus:
        # logger.debug("Getting K8sManagerStatus")
        if refresh:
            self.k8s_status = K8sManagerStatus.PRE_INIT
            logger.debug(f"K8sManagerStatus: {self.k8s_status.value}")

        if self.k8s_status == K8sManagerStatus.PRE_INIT:
            if self.k8s_worker is not None and self.k8s_worker.is_client_initialized():
                self.k8s_status = K8sManagerStatus.WORKER_READY

        if self.k8s_status == K8sManagerStatus.WORKER_READY:
            if self.k8s_worker is not None and self.k8s_worker.are_resources_active():
                self.k8s_status = K8sManagerStatus.RESOURCES_ACTIVE

        logger.debug(f"K8sManagerStatus: {self.k8s_status.value}")
        return self.k8s_status

    ######################################################
    ## Create Resources
    ######################################################

    def create_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot create resources")
            return
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return

        self.k8s_worker.create_resources_dry_run(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def create_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot create resources")
            return False
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return False

        return self.k8s_worker.create_resources(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def validate_resources_are_created(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("Validating resources are created...")
        return True

    ######################################################
    ## Get Resources
    ######################################################

    def get_resource_groups(
        self,
        app_filter: Optional[str] = None,
    ) -> Optional[Dict[str, K8sResourceGroup]]:

        status = self.get_status()
        if not status.can_get_resources():
            logger.debug("Cannot get resources")
            return None
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return None

        return self.k8s_worker.build_k8s_resource_groups(app_filter=app_filter)

    def get_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> Optional[List[K8sResource]]:

        status = self.get_status()
        if not status.can_get_resources():
            logger.debug("Cannot get resources")
            return None
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return None

        return self.k8s_worker.get_resources(
            name_filter=name_filter, type_filter=type_filter, app_filter=app_filter
        )

    ######################################################
    ## Delete Resources
    ######################################################

    def delete_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:

        status = self.get_status()
        if not status.can_delete_resources():
            logger.debug("Cannot delete resources")
            return
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return

        # logger.debug("Deleting resources dry run")
        self.k8s_worker.delete_resources_dry_run(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def delete_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:

        status = self.get_status()
        if not status.can_delete_resources():
            logger.debug("Cannot delete resources")
            return False
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return False

        return self.k8s_worker.delete_resources(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def validate_resources_are_deleted(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("Validating resources are deleted...")
        return True

    ######################################################
    ## Patch Resources
    ######################################################

    def patch_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot patch resources")
            return
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return

        # logger.debug("Deleting resources dry run")
        self.k8s_worker.patch_resources_dry_run(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def patch_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot patch resources")
            return False
        if self.k8s_worker is None:
            logger.debug("No worker available")
            return False

        return self.k8s_worker.patch_resources(
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            auto_confirm=auto_confirm,
        )

    def validate_resources_are_patched(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("Validating resources are patched...")
        return True
