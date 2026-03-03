from enum import Enum
from typing import Optional
import collections

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from google import genai
from google.genai.errors import ClientError
from pydantic import BaseModel, Field
import asyncio

from src.aliases import Message, WorkMail, GeminiClient


class ApplicationStatus(str, Enum):
    """Job application status"""
    CV_RECEIVED = "CV received"
    ACTION_REQUIRED = "action required"
    REJECTED = "rejected"
    HIRED = "hired"


class RecrutationInfo(BaseModel):
    """Info about job recrutation"""
    company: str = Field(description="The company's name")
    position: Optional[str] = Field(description="Job position")
    status: ApplicationStatus
    action: Optional[str] = Field(
        description=("If I need to take an action to be "
                    "recruited (e.g. do some test), "
                    "explain it in one sentence."
                    "Use it only if status is "
                    "'action required'")
                    )


class MailInfo(BaseModel):
    """Mail classification data"""
    recrutation_info: Optional[RecrutationInfo] = Field(
        description=("Set it only if the message is related to specific "
                     "job recrutation I attended. Ignore recrutation ads.")
    )


def get_gemini() -> GeminiClient:
    """Get Gemini client instance"""
    return genai.Client().aio


@backoff.on_exception(backoff.expo,
                    (UnboundLocalError, ClientError),
                    max_tries=32)
async def analyze_mail(topic: str, content: str,
                       gemini: GeminiClient) -> MailInfo:
    """Classify email message"""
    model = "gemini-3-flash-preview"
    prompt = f"Topic: {topic}. Content: {content}"
    response = await gemini.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": MailInfo.model_json_schema()
        }
    )
    return MailInfo.model_validate_json(response.text)


def filter_mails(analyses: MailInfo, messages: list[Message]
                 ) -> list[WorkMail]:
    """Return list of mails related to recrutation"""
    work_mails = []
    for analysis, message in zip(analyses, messages):
        info = analysis.recrutation_info
        if not info:
            continue
        work_mail = {
            "last_update": message["date"],
            "company": info.company,
            "position": info.position if info.position is not None else "-",
            "status": info.status.value,
            "action": info.action if info.action is not None else "-",
            "id": message["id"]
        }
        work_mails.append(work_mail)
    return work_mails


async def analyze_mails(messages: list[Message], gemini: GeminiClient
                        ) -> list[MailInfo]:
    """Classify multiple mails at once"""
    tasks = []
    for message in messages:
        task = analyze_mail(message["topic"],
                            message["content"],
                            gemini)
        tasks.append(task)
    return await asyncio.gather(*tasks)
