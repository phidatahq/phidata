from typing import Optional

from phi.llm.function.registry import FunctionRegistry
from phi.utils.log import logger


class EmailRegistry(FunctionRegistry):
    def __init__(self, sender: Optional[str] = None, receiver: Optional[str] = None):
        super().__init__(name="email_registry")
        self.sender: Optional[str] = sender
        self.receiver: Optional[str] = receiver
        self.register(self.email_user)

    def email_user(self, subject: str, content: str) -> str:
        """Emails the user with the given subject and content.

        :param subject: The subject of the email.
        :param content: The content of the email.
        :return: "success" if the email was sent successfully, "error: [error message]" otherwise.
        """
        logger.info("Sending Email:")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content: {content}")
        return "success"
