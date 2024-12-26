from datetime import datetime
import os
from typing import List
import io
import requests

from phi.run.response import RunResponse
from phi.tools.zoom import ZoomTool
try:
    from pypdf import PdfReader
except ImportError:
    raise ImportError("PyPDF2 is not installed. Please install it using `pip install PyPDF2`")
from phi.agent.agent import Agent
from phi.model.openai.chat import OpenAIChat
from phi.tools.resend_tools import ResendTools
from phi.workflow.workflow import Workflow
from pydantic import BaseModel, Field
from phi.utils.log import logger


class ScreeningResult(BaseModel):
    name: str = Field(description="The name of the candidate")
    email: str = Field(description="The email of the candidate")
    score: float = Field(description="The score of the candidate from 0 to 10")
    feedback: str = Field(description="The feedback for the candidate")


class CandidateScheduledCall(BaseModel):
    name: str = Field(description="The name of the candidate")
    email: str = Field(description="The email of the candidate")
    call_time: str = Field(description="The time of the call")
    url: str = Field(description="The url of the call")


class Email(BaseModel):
    subject: str = Field(description="The subject of the email")
    body: str = Field(description="The body of the email")

current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class EmployeeRecruitmentWorkflow(Workflow):
    screening_agent: Agent = Agent(
        description="You are an HR agent that screens candidates for a job interview.",
        model=OpenAIChat(model="gpt-4o"),
        instructions=[
            "You are an expert HR agent that screens candidates for a job interview.",
            "You are given a candidate's name and resume and job description.",
            "You need to screen the candidate and determine if they are a good fit for the job.", 
            "You need to provide a score for the candidate from 0 to 10.",
            "You need to provide a feedback for the candidate on why they are a good fit or not.",
        ],
        response_model=ScreeningResult
    )

    interview_scheduler_agent: Agent = Agent(
        description="You are an interview scheduler agent that schedules interviews for candidates.",
        model=OpenAIChat(model="gpt-4o"),
        instructions=[
            "You are an interview scheduler agent that schedules interviews for candidates.",
            "You need to schedule interviews for the candidates using the Zoom tool.",
            "You need to schedule the interview for the candidate at the earliest possible time between 10am and 6pm.",
            "Check if the candidate and interviewer are available at the time and if the time is free in the calendar.",
            "You are in IST timezone and the current time is {current_time}. So schedule the call in future time with reference to current time.",
        ],
        tools=[ZoomTool(account_id=os.getenv("ZOOM_ACCOUNT_ID"), client_id=os.getenv("ZOOM_CLIENT_ID"), client_secret=os.getenv("ZOOM_CLIENT_SECRET"))],
        response_model=CandidateScheduledCall
    )

    email_writer_agent: Agent = Agent(
        description="You are an expert email writer agent that writes emails to selected candidates.",
        model=OpenAIChat(model="gpt-4o"),
        instructions=[
            "You are an expert email writer agent that writes emails to selected candidates.",
            "You need to write an email and send it to the candidates using the Resend tool.",
            "You represent the company and the job position.",
            "You need to write an email that is concise and to the point.",
            "You need to write an email that is friendly and professional.",
            "You need to write an email that is not too long and not too short.",
            "You need to write an email that is not too formal and not too informal.",
        ],
        response_model=Email
    )

    email_sender_agent: Agent = Agent(
        description="You are an expert email sender agent that sends emails to selected candidates.",
        model=OpenAIChat(model="gpt-4o"),
        instructions=[
            "You are an expert email sender agent that sends emails to selected candidates.",
            "You need to send an email to the candidate using the Resend tool.",
            "You will be given the email subject and body and you need to send it to the candidate.",
        ],
        tools=[ResendTools(from_email="manthan@phidata.com")]
    )

    def extract_text_from_pdf(self, pdf_url: str) -> str:
        """Download PDF from URL and extract text content"""
        try:
            # Download PDF content
            response = requests.get(pdf_url)
            response.raise_for_status()
            
            # Create PDF reader object
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text()
                
            return text_content
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return ""

    def run(self, candidate_resume_urls: List[str], job_description: str) -> RunResponse:
        selected_candidates = []
        for resume_url in candidate_resume_urls:
            # Extract text from PDF resume
            if resume_url in self.session_state:
                resume_content = self.session_state[resume_url]
            else:
                resume_content = self.extract_text_from_pdf(resume_url)
                self.session_state[resume_url] = resume_content
            screening_result = None

            if resume_content:
                # Screen the candidate
                input = f"Candidate resume: {resume_content}, Job description: {job_description}"
                screening_result = self.screening_agent.run(input)
                logger.info(screening_result)
            else:
                logger.error(f"Could not process resume from URL: {resume_url}")

            if screening_result.content.score > 7.0:
                selected_candidates.append(screening_result.content)

        for selected_candidate in selected_candidates:
            input = f"Schedule a 1hr call with Candidate name: {selected_candidate.name}, Candidate email: {selected_candidate.email} and the interviewer would be Manthan Gupts with email manthan@phidata.com"
            scheduled_call = self.interview_scheduler_agent.run(input)
            logger.info(scheduled_call.content)
            

            if scheduled_call.content.url and scheduled_call.content.call_time:
                input = f"Write an email to Candidate name: {selected_candidate.name}, Candidate email: {selected_candidate.email} for the call scheduled at {scheduled_call.content.call_time} with the url {scheduled_call.content.url} and congratulate them for the interview from Manthan Gupta designation Senior Software Engineer and email manthan@phidata.com"
                email = self.email_writer_agent.run(input)
                logger.info(email.content)

                if email.content:
                    input = f"Send email to {selected_candidate.email} with subject {email.content.subject} and body {email.content.body}"
                    self.email_sender_agent.run(input)

        return RunResponse(
            content=f"Selected {len(selected_candidates)} candidates for the interview.",
        )


if __name__ == "__main__":
    workflow = EmployeeRecruitmentWorkflow()
    result = workflow.run(
        candidate_resume_urls=["https://recruitment-workflow.s3.us-west-2.amazonaws.com/Manthan_Gupta_Resume_2.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAXH3FLC3KAVNSDRND%2F20241226%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20241226T131854Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEFUaCXVzLXdlc3QtMiJHMEUCIQDa6MKRU4%2FRB%2FLmuQ9iWXOu2YcWK8iNLNz5WgH2tEgCXgIgAhQopc6xpZ1g2ZDtn356%2F75O1G%2Fl%2FRuYgg8TDczAJ8YqgQMILhABGgw0OTc4OTE4NzQ1MTYiDIypPFhQdqC7kTBWASreAi6Ec1%2B32OHoG39evHH44MXAEGrQMKeW5t%2BEmSpr4Bw0Z8Pl8%2BRrlw3GUbHUG169iKhkeepCrtsXNRQEvpE3B78wg2EfL%2BsyAD7SCgTNoHoTseXuc%2Bhvsx9m9XPOwNs9NKxQcnOEDn%2F5BzjcPbizS4xIqqAJqaN77WMOPddP4wZw35Q3zAOtsfAY3Xrduwf60zGFPWtBLYGb0GiCNwZQCX9jUaNHNhaXLeEiyIA9Qmsrb5pOS%2BEbfzlo1AmOSFUBqTGDUWDWs5NK8bpaC8Ol20e6DOjyS15XEKAExnkz1ttwpcNlWUNSr4fOaL3GzM%2FKAAe84jEhSDu6bBeXLWhW09Psvn2EwaMLAbUYzJyG04OzqSfnMKx8W60UaY5ZbaoYK2dszVbwA%2Fx9xm8Gh1ZpnsM6%2FFH%2FGR1gm6lm4of%2BW8Rr8AmvbrEkCXHUUsvypWoEw%2Fj4ipU6fTMJ3kp86WBTMOWatbsGOrMCwQyfgc%2BhiWYDGcRoVzriUQHdT68r%2B5Ad4uliSxV7qSF1bBLnM%2FXiYWxBnYC5983zoyFEYaPlorET85Z7LKeV%2Bj%2F9Cb6AC%2FuymbtYru9JbHZa3il86xq1i8bzO9liyCYE3hxqyOL2Bat%2Fi0sf0%2BXUQdqzNY3BL0N4O%2FS0dHjtCfaf4TPzy76626iymKB7HrhkiPbrx0z8i6LVKNxLizRW7fosyh1IG0TkKgYMoBjA7DkED4L5lFhxTncZP9vEUPBiZ5PYJAr1D%2FGPQQAaCZ%2FWSxE2BL5lvywAA4QYPzwVH1wwJYaxp6swaXBykA6XUbey0ZoJgVP0G%2FHIv6%2BDqR5xcA428LAiO4khqpw4S7VXprLUPwjFthQOisX5YSWqsvVFN6eCfJThQgQjHsIZLGWO%2Bwkcow%3D%3D&X-Amz-Signature=b8a995478dfa676c1f0254fc2c1f6ee8b935eb80a25efde5a6e1303da26f454b&X-Amz-SignedHeaders=host&response-content-disposition=inline"],
        job_description="""
            We are hiring for backend and systems engineers! 
            Join our team building the future of agentic software

            Apply if:
            🧠 You know your way around Python, typescript, docker, and AWS.
            ⚙️ Love to build in public and contribute to open source.
            🚀 Are ok dealing with the pressure of an early-stage startup.
            🏆 Want to be a part of the biggest technological shift since the internet.
            🌟 Bonus: experience with infrastructure as code.
            🌟 Bonus: starred Phidata repo.

            """
    )
    print(result.content)