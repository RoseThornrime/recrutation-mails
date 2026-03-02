from enum import Enum
from typing import Optional
import collections

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from google import genai
from pydantic import BaseModel, Field
import asyncio


class ApplicationStatus(str, Enum):
    CV_RECEIVED = "CV received"
    ACTION_REQUIRED = "action required"
    REJECTED = "rejected"
    HIRED = "hired"


class RecrutationInfo(BaseModel):
    company: str = Field(description="The company's name")
    position: Optional[str] = Field(description="Job position")
    status: Optional[ApplicationStatus]
    action: Optional[str] = Field(description=
                                  ("If I need to take an action to be "
                                   "recruited (e.g. do some test), "
                                   "explain it in one sentence, in english")
                                  )


class MailInfo(BaseModel):
    is_recrutation: bool = Field(
        description="Is this related to job recrutation?"
    )
    recrutation_info: Optional[RecrutationInfo]


def get_gemini():
    return genai.Client().aio


@backoff.on_exception(backoff.expo, UnboundLocalError, max_tries=8)
async def analyze_mail(topic, content, gemini):
    model = "gemini-3-flash-preview"
    prompt = f"Topic: {topic}. Content: {content}"
    try:
        response = await gemini.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": MailInfo.model_json_schema()
            }
        )
    except genai.errors.ServerError as error:
        print(f"An error occurred: {error}")
    return MailInfo.model_validate_json(response.text)


def filter_mails(analyses, messages):
    work_mails = []
    for analysis, message in zip(analyses, messages):
        if not analysis.is_recrutation:
            continue
        info = analysis.recrutation_info
        mail_info = {
            "last_update": message["date"],
            "company": info.company,
            "position": info.position if info.position is not None else "",
            "status": info.status.value,
            "action": info.action if info.action is not None else "",
            "id": message["id"]
        }
        work_mails.append(mail_info)
    return work_mails


async def analyze_mails(messages, gemini):
    tasks = []
    for message in messages:
        task = analyze_mail(message["topic"],
                            message["content"],
                            gemini)
        tasks.append(task)
    return await asyncio.gather(*tasks)
