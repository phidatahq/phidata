from pathlib import Path
from typing import Optional, List, Dict

from phidata.infra.aws.args import AwsArgs
from phidata.infra.aws.enums import AwsManagerStatus
from phidata.infra.aws.exceptions import AwsArgsException
from phidata.infra.aws.resource.types import AwsResourceType
from phidata.infra.aws.worker import AwsWorker
from phidata.infra.k8s.args import K8sArgs
from phidata.infra.k8s.exceptions import K8sWorkerException
from phidata.infra.k8s.worker import K8sWorker
from phidata.utils.cli_console import print_error, print_info
from phidata.utils.log import logger


class AwsManager:
    def __init__(self, aws_args: AwsArgs):
        if aws_args is None or not isinstance(aws_args, AwsArgs):
            raise AwsArgsException("Invalid AwsArgs")
        if aws_args.workspace_root_path is None or not isinstance(
            aws_args.workspace_root_path, Path
        ):
            raise AwsArgsException("workspace_root_path invalid")
        if aws_args.workspace_config_file_path is None or not isinstance(
            aws_args.workspace_config_file_path, Path
        ):
            raise AwsArgsException("workspace_config_file_path invalid")

        self.aws_args: AwsArgs = aws_args
        self.aws_worker: Optional[AwsWorker] = AwsWorker(self.aws_args)
        self.aws_status: AwsManagerStatus = AwsManagerStatus.PRE_INIT
        logger.debug("**-+-** AwsManager created")

    def get_status(self, refresh: bool = False) -> AwsManagerStatus:
        # logger.debug("Getting AwsManagerStatus")
        if refresh:
            self.aws_status = AwsManagerStatus.PRE_INIT
            logger.debug(f"AwsManagerStatus: {self.aws_status.value}")

        if self.aws_status == AwsManagerStatus.PRE_INIT:
            if self.aws_worker is not None and self.aws_worker.is_client_initialized():
                self.aws_status = AwsManagerStatus.WORKER_READY

        if self.aws_status == AwsManagerStatus.WORKER_READY:
            if (
                self.aws_worker is not None
                and self.aws_worker.are_resources_initialized()
            ):
                self.aws_status = AwsManagerStatus.RESOURCES_INIT

        logger.debug(f"AwsManagerStatus: {self.aws_status.value}")
        return self.aws_status

    ######################################################
    ## Create Resources
    ######################################################

    def create_resources_dry_run(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> None:

        status = self.get_status()
        if not status.can_create_resources():
            print_error("Cannot create AwsResources")
            return
        if self.aws_worker is None:
            print_error("AWSWorker not available")
            return

        # logger.debug("Creating resources dry run")
        self.aws_worker.create_resources_dry_run(
            name_filter=name_filter, type_filter=type_filter
        )

    def create_resources(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot create AwsResources")
            return False
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return False

        return self.aws_worker.create_resources(
            name_filter=name_filter, type_filter=type_filter
        )

    def validate_resources_are_created(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        logger.debug("Validating resources are created...")
        return True

    ######################################################
    ## Read Resources
    ######################################################

    def read_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Optional[Dict[str, List[AwsResourceType]]]:

        status = self.get_status()
        if not status.can_get_resources():
            logger.debug("Cannot get AwsResources")
            return None
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return None

        return self.aws_worker.read_resources(name_filter, type_filter)

    ######################################################
    ## Delete Resources
    ######################################################

    def delete_resources_dry_run(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> None:

        status = self.get_status()
        if not status.can_delete_resources():
            logger.debug("Cannot delete AwsResources")
            return
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return

        # logger.debug("Deleting resources dry run")
        self.aws_worker.delete_resources_dry_run(
            name_filter=name_filter, type_filter=type_filter
        )

    def delete_resources(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        status = self.get_status()
        if not status.can_delete_resources():
            logger.debug("Cannot delete AwsResources")
            return False
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return False

        return self.aws_worker.delete_resources(
            name_filter=name_filter, type_filter=type_filter
        )

    def validate_resources_are_deleted(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        logger.debug("Validating resources are deleted...")
        return True

    ######################################################
    ## Patch Resources
    ######################################################

    def patch_resources_dry_run(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> None:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot patch AwsResources")
            return
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return

        # logger.debug("Deleting resources dry run")
        self.aws_worker.patch_resources_dry_run(
            name_filter=name_filter, type_filter=type_filter
        )

    def patch_resources(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        status = self.get_status()
        if not status.can_create_resources():
            logger.debug("Cannot patch AwsResources")
            return False
        if self.aws_worker is None:
            logger.debug("AWSWorker not available")
            return False

        return self.aws_worker.patch_resources(
            name_filter=name_filter, type_filter=type_filter
        )

    def validate_resources_are_patched(
        self, name_filter: Optional[str] = None, type_filter: Optional[str] = None
    ) -> bool:

        logger.debug("Validating resources are patched...")
        return True
