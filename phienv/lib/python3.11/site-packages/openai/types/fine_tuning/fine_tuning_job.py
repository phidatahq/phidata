# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal

from ..._models import BaseModel
from .fine_tuning_job_wandb_integration_object import FineTuningJobWandbIntegrationObject

__all__ = [
    "FineTuningJob",
    "Error",
    "Hyperparameters",
    "Method",
    "MethodDpo",
    "MethodDpoHyperparameters",
    "MethodSupervised",
    "MethodSupervisedHyperparameters",
]


class Error(BaseModel):
    code: str
    """A machine-readable error code."""

    message: str
    """A human-readable error message."""

    param: Optional[str] = None
    """The parameter that was invalid, usually `training_file` or `validation_file`.

    This field will be null if the failure was not parameter-specific.
    """


class Hyperparameters(BaseModel):
    batch_size: Union[Literal["auto"], int, None] = None
    """Number of examples in each batch.

    A larger batch size means that model parameters are updated less frequently, but
    with lower variance.
    """

    learning_rate_multiplier: Union[Literal["auto"], float, None] = None
    """Scaling factor for the learning rate.

    A smaller learning rate may be useful to avoid overfitting.
    """

    n_epochs: Union[Literal["auto"], int, None] = None
    """The number of epochs to train the model for.

    An epoch refers to one full cycle through the training dataset.
    """


class MethodDpoHyperparameters(BaseModel):
    batch_size: Union[Literal["auto"], int, None] = None
    """Number of examples in each batch.

    A larger batch size means that model parameters are updated less frequently, but
    with lower variance.
    """

    beta: Union[Literal["auto"], float, None] = None
    """The beta value for the DPO method.

    A higher beta value will increase the weight of the penalty between the policy
    and reference model.
    """

    learning_rate_multiplier: Union[Literal["auto"], float, None] = None
    """Scaling factor for the learning rate.

    A smaller learning rate may be useful to avoid overfitting.
    """

    n_epochs: Union[Literal["auto"], int, None] = None
    """The number of epochs to train the model for.

    An epoch refers to one full cycle through the training dataset.
    """


class MethodDpo(BaseModel):
    hyperparameters: Optional[MethodDpoHyperparameters] = None
    """The hyperparameters used for the fine-tuning job."""


class MethodSupervisedHyperparameters(BaseModel):
    batch_size: Union[Literal["auto"], int, None] = None
    """Number of examples in each batch.

    A larger batch size means that model parameters are updated less frequently, but
    with lower variance.
    """

    learning_rate_multiplier: Union[Literal["auto"], float, None] = None
    """Scaling factor for the learning rate.

    A smaller learning rate may be useful to avoid overfitting.
    """

    n_epochs: Union[Literal["auto"], int, None] = None
    """The number of epochs to train the model for.

    An epoch refers to one full cycle through the training dataset.
    """


class MethodSupervised(BaseModel):
    hyperparameters: Optional[MethodSupervisedHyperparameters] = None
    """The hyperparameters used for the fine-tuning job."""


class Method(BaseModel):
    dpo: Optional[MethodDpo] = None
    """Configuration for the DPO fine-tuning method."""

    supervised: Optional[MethodSupervised] = None
    """Configuration for the supervised fine-tuning method."""

    type: Optional[Literal["supervised", "dpo"]] = None
    """The type of method. Is either `supervised` or `dpo`."""


class FineTuningJob(BaseModel):
    id: str
    """The object identifier, which can be referenced in the API endpoints."""

    created_at: int
    """The Unix timestamp (in seconds) for when the fine-tuning job was created."""

    error: Optional[Error] = None
    """
    For fine-tuning jobs that have `failed`, this will contain more information on
    the cause of the failure.
    """

    fine_tuned_model: Optional[str] = None
    """The name of the fine-tuned model that is being created.

    The value will be null if the fine-tuning job is still running.
    """

    finished_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the fine-tuning job was finished.

    The value will be null if the fine-tuning job is still running.
    """

    hyperparameters: Hyperparameters
    """The hyperparameters used for the fine-tuning job.

    This value will only be returned when running `supervised` jobs.
    """

    model: str
    """The base model that is being fine-tuned."""

    object: Literal["fine_tuning.job"]
    """The object type, which is always "fine_tuning.job"."""

    organization_id: str
    """The organization that owns the fine-tuning job."""

    result_files: List[str]
    """The compiled results file ID(s) for the fine-tuning job.

    You can retrieve the results with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    seed: int
    """The seed used for the fine-tuning job."""

    status: Literal["validating_files", "queued", "running", "succeeded", "failed", "cancelled"]
    """
    The current status of the fine-tuning job, which can be either
    `validating_files`, `queued`, `running`, `succeeded`, `failed`, or `cancelled`.
    """

    trained_tokens: Optional[int] = None
    """The total number of billable tokens processed by this fine-tuning job.

    The value will be null if the fine-tuning job is still running.
    """

    training_file: str
    """The file ID used for training.

    You can retrieve the training data with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    validation_file: Optional[str] = None
    """The file ID used for validation.

    You can retrieve the validation results with the
    [Files API](https://platform.openai.com/docs/api-reference/files/retrieve-contents).
    """

    estimated_finish: Optional[int] = None
    """
    The Unix timestamp (in seconds) for when the fine-tuning job is estimated to
    finish. The value will be null if the fine-tuning job is not running.
    """

    integrations: Optional[List[FineTuningJobWandbIntegrationObject]] = None
    """A list of integrations to enable for this fine-tuning job."""

    method: Optional[Method] = None
    """The method used for fine-tuning."""
