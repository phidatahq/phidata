from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel


class RunContext(BaseModel):
    # Run specific variables
    run_date: datetime
    dry_run: bool = False
    detach: bool = False
    run_status: bool = False
    run_env: Optional[str] = None
    run_env_vars: Optional[Dict[str, str]] = None
    run_params: Optional[Dict[str, str]] = None


class PathContext(BaseModel):
    # Env specific path variables - their values are different on
    # local, docker or cloud environments.
    # These are updated by `phi wf run` for local runs
    # And are provided as Environment variables on containers

    scripts_dir: Optional[Path] = None
    storage_dir: Optional[Path] = None
    meta_dir: Optional[Path] = None
    products_dir: Optional[Path] = None
    notebooks_dir: Optional[Path] = None
    workspace_config_dir: Optional[Path] = None
    workflow_file: Optional[Path] = None


class ContainerPathContext(BaseModel):
    workspace_name: Optional[str] = None
    workspace_root: Optional[str] = None
    workspace_parent: Optional[str] = None
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    meta_dir: Optional[str] = None
    products_dir: Optional[str] = None
    notebooks_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_config_dir: Optional[str] = None
    requirements_file: Optional[str] = None


class AirflowContext(BaseModel):
    ds: Optional[Any] = None
    ds_nodash: Optional[Any] = None
    logical_date: Optional[Any] = None
    data_interval_start: Optional[Any] = None
    data_interval_end: Optional[Any] = None

    ts: Optional[Any] = None
    ts_nodash: Optional[Any] = None

    test_mode: Optional[Any] = None
    conn: Optional[Any] = None

    conf: Optional[Any] = None
    dag: Optional[Any] = None
    dag_run: Optional[Any] = None
    task: Optional[Any] = None
    task_instance: Optional[Any] = None


class DockerContext(BaseModel):
    pass


class K8sContext(BaseModel):
    pass
