from google import genai
from pydantic import BaseModel, Field
from typing import Optional


class RecrutationStatus(BaseModel):
    company: str = Field(description="The company's name")
    position: str = Field(description="Job position")
    status: str = Field(description="'CV received', 'Action required: [describe it here in one sentence]', 'Rejected', 'Success'")


class MailInfo(BaseModel):
    is_recrutation: bool = Field(
        description="Is this related to job recrutation?"
    )
    recrutation_status: Optional[RecrutationStatus]



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
