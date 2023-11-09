from typing import Any, Optional
from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict

from phi.assistant.exceptions import FileIdNotSet
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.file_object import FileObject as OpenAIFile
    from openai.types.file_deleted import FileDeleted as OpenAIFileDeleted
except ImportError:
    logger.error("`openai` not installed")
    raise


class File(BaseModel):
    # -*- File settings
    # File id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always file.
    object: Optional[str] = None

    # The size of the file, in bytes.
    bytes: Optional[int] = None

    # The name of the file.
    filename: Optional[str] = None
    # The intended purpose of the file.
    # Supported values are fine-tune, fine-tune-results, assistants, and assistants_output.
    purpose: Literal["fine-tune", "assistants"] = "assistants"

    # The Unix timestamp (in seconds) for when the file was created.
    created_at: Optional[int] = None

    openai: Optional[OpenAI] = None
    openai_file: Optional[OpenAIFile] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def read(self) -> Any:
        raise NotImplementedError

    def load_from_openai(self, openai_file: OpenAIFile):
        self.id = openai_file.id
        self.object = openai_file.object
        self.created_at = openai_file.created_at

    def upload(self) -> OpenAIFile:
        self.openai_file = self.client.files.create(file=self.read(), purpose=self.purpose)
        self.load_from_openai(self.openai_file)
        return self.openai_file

    def download(self, use_cache: bool = True) -> str:
        try:
            file_to_download = self.get(use_cache=use_cache)
            if file_to_download is not None:
                content = self.client.files.retrieve_content(file_id=file_to_download.id)
                return content
        except FileIdNotSet:
            logger.warning("File not available")
            raise

    def get(self, use_cache: bool = True) -> OpenAIFile:
        if self.openai_file is not None and use_cache:
            return self.openai_file

        _file_id = self.id or self.openai_file.id if self.openai_file else None
        if _file_id is not None:
            self.openai_file = self.client.files.retrieve(file_id=_file_id)
            self.load_from_openai(self.openai_file)
            return self.openai_file
        raise FileIdNotSet("File.id not set")

    def get_id(self) -> str:
        return self.get().id

    def delete(self) -> OpenAIFileDeleted:
        try:
            file_to_delete = self.get()
            if file_to_delete is not None:
                deletion_status = self.client.files.delete(
                    file_id=file_to_delete.id,
                )
                return deletion_status
        except FileIdNotSet:
            logger.warning("File not available")
            raise
