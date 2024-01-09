from typing import Any, Optional, Dict
from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict

from phi.assistant.openai.exceptions import FileIdNotSet
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
    name: Optional[str] = None
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

    # The current status of the file, which can be either `uploaded`, `processed`, or `error`.
    status: Optional[Literal["uploaded", "processed", "error"]] = None
    status_details: Optional[str] = None

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

    def get_filename(self) -> Optional[str]:
        return self.filename

    def load_from_openai(self, openai_file: OpenAIFile):
        self.id = openai_file.id
        self.object = openai_file.object
        self.bytes = openai_file.bytes
        self.created_at = openai_file.created_at
        self.filename = openai_file.filename
        self.status = openai_file.status
        self.status_details = openai_file.status_details

    def create(self) -> "File":
        self.openai_file = self.client.files.create(file=self.read(), purpose=self.purpose)
        self.load_from_openai(self.openai_file)
        logger.debug(f"File created: {self.openai_file.id}")
        logger.debug(f"File: {self.openai_file}")
        return self

    def get_id(self) -> Optional[str]:
        return self.id or self.openai_file.id if self.openai_file else None

    def get_using_filename(self) -> Optional[OpenAIFile]:
        file_list = self.client.files.list(purpose=self.purpose)
        file_name = self.get_filename()
        if file_name is None:
            return None

        logger.debug(f"Getting id for: {file_name}")
        for file in file_list:
            if file.filename == file_name:
                logger.debug(f"Found file: {file.id}")
                return file
        return None

    def get_from_openai(self) -> OpenAIFile:
        _file_id = self.get_id()
        if _file_id is None:
            oai_file = self.get_using_filename()
        else:
            oai_file = self.client.files.retrieve(file_id=_file_id)

        if oai_file is None:
            raise FileIdNotSet("File.id not set")

        self.openai_file = oai_file
        self.load_from_openai(self.openai_file)
        return self.openai_file

    def get(self, use_cache: bool = True) -> "File":
        if self.openai_file is not None and use_cache:
            return self

        self.get_from_openai()
        return self

    def get_or_create(self, use_cache: bool = True) -> "File":
        try:
            return self.get(use_cache=use_cache)
        except FileIdNotSet:
            return self.create()

    def download(self, path: Optional[str] = None, suffix: Optional[str] = None) -> str:
        from tempfile import NamedTemporaryFile

        try:
            file_to_download = self.get_from_openai()
            if file_to_download is not None:
                logger.debug(f"Downloading file: {file_to_download.id}")
                response = self.client.files.with_raw_response.retrieve_content(file_id=file_to_download.id)
                if path:
                    with open(path, "wb") as f:
                        f.write(response.content)
                    return path
                else:
                    with NamedTemporaryFile(delete=False, mode="wb", suffix=f"{suffix}") as temp_file:
                        temp_file.write(response.content)
                        temp_file_path = temp_file.name
                    return temp_file_path
            raise ValueError("File not available")
        except FileIdNotSet:
            logger.warning("File not available")
            raise

    def delete(self) -> OpenAIFileDeleted:
        try:
            file_to_delete = self.get_from_openai()
            if file_to_delete is not None:
                deletion_status = self.client.files.delete(
                    file_id=file_to_delete.id,
                )
                logger.debug(f"File deleted: {file_to_delete.id}")
                return deletion_status
        except FileIdNotSet:
            logger.warning("File not available")
            raise

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            include={
                "filename",
                "id",
                "object",
                "bytes",
                "purpose",
                "created_at",
            },
        )

    def pprint(self):
        """Pretty print using rich"""
        from rich.pretty import pprint

        pprint(self.to_dict())

    def __str__(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=4)
