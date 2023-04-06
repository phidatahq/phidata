from phidata.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Production container images
#

prd_images = []

# -*- Airflow image
prd_airflow_image = DockerImage(
    name=f"{ws_settings.image_repo}/airflow-{ws_settings.image_suffix}",
    tag=ws_settings.prd_env,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/prd/images/airflow.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

if ws_settings.prd_airflow_enabled and ws_settings.build_images:
    prd_images.append(prd_airflow_image)

# -*- Jupyter image
prd_jupyter_image = DockerImage(
    name=f"{ws_settings.image_repo}/jupyter-{ws_settings.image_suffix}",
    tag=ws_settings.prd_env,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/prd/images/jupyter.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

if ws_settings.prd_jupyter_enabled and ws_settings.build_images:
    prd_images.append(prd_jupyter_image)

# -*- Superset image
prd_superset_image = DockerImage(
    name=f"{ws_settings.image_repo}/superset-{ws_settings.image_suffix}",
    tag=ws_settings.prd_env,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/prd/images/superset.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

if ws_settings.prd_superset_enabled and ws_settings.build_images:
    prd_images.append(prd_superset_image)

# -*- Databox image
prd_databox_image = DockerImage(
    name=f"{ws_settings.image_repo}/databox-{ws_settings.image_suffix}",
    tag=ws_settings.prd_env,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/prd/images/databox.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

if ws_settings.prd_databox_enabled and ws_settings.build_images:
    prd_images.append(prd_databox_image)
