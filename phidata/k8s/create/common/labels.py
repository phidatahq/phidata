from typing import Dict, Optional


def create_component_labels_dict(
    component_name: str, app_name: str, labels: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    _labels = {
        "app.kubernetes.io/component": component_name,
        "app.kubernetes.io/app": app_name,
    }
    if labels:
        _labels.update(labels)

    return _labels
