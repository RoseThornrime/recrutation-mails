from google import genai


def get_gemini():
    return genai.Client().aio


async def analyze_mail(topic, content, gemini):
    model = "gemini-3-flash-preview"
    contents = (f"Is it work related? Answer shortly using format:",
                " 'work: <company name>' if yes, or 'no' otherwise.",
                f"The title to read is: '{topic}'.",
                f"The content to read is: '{content}.") 
    try:
        response = await gemini.models.generate_content(
            model=model,
            contents=contents
        )
    except genai.errors.ServerError as error:
        print(f"An error occurred: {error}")
    return response.text
