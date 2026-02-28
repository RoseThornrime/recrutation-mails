from google import genai
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


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
                                  ("If an additional action is required, "
                                   "explain it in one sentence")
                                  )


class MailInfo(BaseModel):
    is_recrutation: bool = Field(
        description="Is this related to job recrutation?"
    )
    recrutation_status: Optional[RecrutationInfo]


def get_gemini():
    return genai.Client().aio


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
