from typing import Optional

from phi.tools import ToolRegistry
from phi.utils.log import logger

try:
    import resend  # type: ignore
except ImportError:
    raise ImportError("`resend` not installed. Please install using `pip install resend`.")


class ResendTools(ToolRegistry):
    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        super().__init__(name="resend_tools")

        self.api_key = api_key

        self.register(self.send_email)

    def send_email(self, email: str, subject: str, body: str) -> str:
        """Send an email using the Resend API. Returns if the email was sent successfully or an error message.

        :email: The email address to send the email to.
        :subject: The subject of the email.
        :body: The body of the email.
        :return: A string indicating if the email was sent successfully or an error message.
        """

        if not self.api_key:
            return "Please provide an API key"
        if not email:
            return "Please provide an email address"

        logger.info(f"Sending email to: {email}")

        resend.api_key = self.api_key

        try:
            params = {
                "from": "phidata <info@phidata.com>",
                "to": email,
                "subject": f"phidata: {subject}",
                "html": body,
            }

            resend.Emails.send(params)

            return "Email sent"
        except Exception as e:
            logger.warning(f"Failed to send email {e}")
            return f"Error: {e}"
