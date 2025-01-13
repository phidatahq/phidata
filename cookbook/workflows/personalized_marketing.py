"""
This workflow demonstrates how to create a personalized marketing email for a given company.

Steps to run the workflow:

1. Set up OpenAI and Resend API keys in the environment variables.
2. Update the `company_info` dictionary with the details of the companies you want to target. (Note: If the provided email is unreachable, a fallback will be attempted using scraped email addresses from the website.)
4. Customize the email template with placeholders for the subject line, recipient name, sender name, and other details.
4. Run the workflow by executing the script.
5. The workflow will scrape the website of each company, extract relevant information, and generate and send a personalized email.
"""

from typing import Optional, Iterator, Dict, Any, List

from pydantic import BaseModel, Field
from pydantic import ValidationError

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunResponse
from phi.tools.firecrawl import FirecrawlTools
from phi.tools.resend_tools import ResendTools
from phi.utils.pprint import pprint_run_response
from phi.utils.log import logger
from email_validator import validate_email, EmailNotValidError

company_info: Dict = {
    "Phidata": {
        "website": "https://www.phidata.com/",
        "email": "<insert-receiver-email>",
        "contact_name": "<insert-receiver-name>",
        "position": "<insert-receiver-position>",
    },
}

sender_details_dict: Dict = {
    "name": "<insert-sender-name>",
    "email": "<insert-sender-email>",
    "organization": "<insert-sender-organization>",
    "calendar Link": "<insert-calendar-link>",
    "service_offered": "<insert-service-offered>",
}
sender_details = ", ".join(f"{k}: {v}" for k, v in sender_details_dict.items())

# Email template with placeholders
email_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #0073e6;
        }
        a {
            color: #0073e6;
            text-decoration: none;
        }
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: #0073e6;
            color: #fff;
            text-align: center;
            border-radius: 5px;
            text-decoration: none;
            margin-top: 15px;
        }
        .button:hover {
            background-color: #005bb5;
        }
    </style>
</head>
<body>
    <h1>[SUBJECT_LINE]</h1>

    <p>Hi <strong>[RECIPIENT_NAME]</strong>,</p>

    <p>I’m <strong>[SENDER_NAME]</strong>. I was impressed by <strong>[COMPANY_NAME]</strong>’s <em>[UNIQUE_ATTRIBUTE]</em>. It’s clear you have a strong vision for serving your customers.</p>

    <p>At <strong>[YOUR_ORGANIZATION]</strong>, we provide tailored solutions to help businesses stand out in today’s competitive market. After reviewing your online presence, I noticed a few opportunities that, if optimized, could significantly boost your brand’s visibility and engagement.</p>

    <p>To showcase how we can help, I’m offering a <strong>[FREE_INITIAL_SERVICE]</strong>. This assessment will highlight key areas for growth and provide actionable steps to improve your online impact.</p>

    <p>Let’s discuss how we can work together to achieve these goals. Could we schedule a quick call? Please let me know a time that works for you or feel free to book directly here:</p>

    <p><a href="[CALENDAR_LINK]" class="button">Book a Meeting</a></p>

    <p>Best regards,</p>
    <p><strong>[SENDER_NAME]</strong><br>[SENDER_CONTACT_INFORMATION]</p>
</body>
</html>
"""


class CompanyInfo(BaseModel):
    company_name: str = Field(..., description="Name of the company.")
    motto: Optional[str] = Field(None, description="Company motto or tagline.")
    core_business: Optional[str] = Field(None, description="Primary business of the company.")
    unique_selling_point: Optional[str] = Field(None, description="What sets the company apart from its competitors.")
    email_address: Optional[str] = Field(None, description="Email address of the company.")


def company_info_to_string(contact_email: str, company: CompanyInfo) -> str:
    """
    Construct a single string description of the company, omitting None fields.
    If company.email_address is None, use fallback_email.
    """
    parts: List[str] = [company.company_name]

    if company.motto:
        parts.append(f"whose motto is '{company.motto}'")

    if company.core_business:
        parts.append(f"specializing in {company.core_business}")

    if company.unique_selling_point:
        parts.append(f"known for {company.unique_selling_point}")

    # Determine email address to use
    try:
        email_info = validate_email(contact_email, check_deliverability=True)
        contact_email = email_info.normalized
    except EmailNotValidError:
        logger.warning(f"Invalid email address: {contact_email}. Using fallback.")
        contact_email = company.email_address if company.email_address else "unreachable"
    parts.append(f"contactable at {contact_email}")

    return ", ".join(parts) + "."


class PersonalisedMarketing(Workflow):
    # This description is only used in the workflow UI
    description: str = "Generate a personalised email for a given contact."

    scraper: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[FirecrawlTools()],
        description="Given a company name, scrape the website for important information related to the company.",
        response_model=CompanyInfo,
        structured_outputs=True,
    )

    email_creator: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=[
            "You will be provided with information about a company and a contact person.",
            "Use this information to create a personalised email to reach out to the contact person.",
            "Introduce yourself and your purpose for reaching out.",
            "Be extremely polite and professional.",
            "Offer the services of your organization and suggest a meeting or call.",
            f"Send the email as: {sender_details}",
            "Use the following template to structure your email:",
            email_template,
            "Then finally, use the resend tool to send the email.",
        ],
        tools=[ResendTools(from_email=sender_details_dict["email"])],
        markdown=False,
    )

    def run(self, *args: Any, **kwargs: Any) -> Iterator[RunResponse]:
        """
        Iterates over companies, scrapes each website for data,
        composes a personalized email, and sends it out.
        """
        for company_key, info in company_info.items():
            logger.info(f"Processing company: {company_key}")

            # 1. Scrape the website
            scraper_response = self.scraper.run(info["website"])

            if not scraper_response or not scraper_response.content:
                logger.warning(f"No data returned by scraper for {company_key}. Skipping.")
                continue

            # 2. Validate or parse the scraped content
            try:
                company_extracted_data = scraper_response.content
                if not isinstance(company_extracted_data, CompanyInfo):
                    logger.error(f"Scraped data for {company_key} is not a CompanyInfo instance. Skipping.")
                    continue
            except ValidationError as e:
                logger.error(f"Validation error for {company_key}: {e}")
                continue

            # 3. Create a descriptive string
            message = company_info_to_string(info["email"], company_extracted_data)

            # 4. Generate and send the email
            response_stream = self.email_creator.run(message, stream=True)
            yield from response_stream


# Run the workflow if the script is executed directly
if __name__ == "__main__":
    # Instantiate and run the workflow
    create_personalised_email = PersonalisedMarketing()
    email_responses: Iterator[RunResponse] = create_personalised_email.run()

    # Print the responses
    pprint_run_response(email_responses, markdown=True)
