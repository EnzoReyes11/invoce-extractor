import os

from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin
from google.adk.tools import ToolContext
from google.genai import types

from .model import ExtractionResult

load_dotenv()

GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID")

genai_client = genai.Client(
    vertexai=GOOGLE_GENAI_USE_VERTEXAI,
    project=GOOGLE_CLOUD_PROJECT,
    location=GOOGLE_CLOUD_LOCATION,
)


async def get_pdf_from_artifact(filename: str, tool_context: ToolContext) -> bytes:
    """
    Loads a specific PDF from saved artifacts and returns its byte content

    Args:
        filename: Name of PDF artifact file to load
        tool_context: context object provided by ADK framework

    Returns:
        Byte content (bytes) of PDF file

    Raises:
        ValueError: If the artifact is not found or is not a PDF
        RuntimeError: For unexpected storage or other errors
    """
    try:
        pdf_artifact = await tool_context.load_artifact(filename=filename)

        if (
            pdf_artifact
            and hasattr(pdf_artifact, "inline_data")
            and pdf_artifact.inline_data
        ):
            if pdf_artifact.inline_data.mime_type == "application/pdf":
                print(f"Successfully loaded PDF artifact '{filename}'.")

                # Extract and return the raw byte content
                pdf_bytes = pdf_artifact.inline_data.data
                return pdf_bytes
            elif pdf_artifact.inline_data.mime_type.startswith("image/"):
                print(f"Successfully loaded Image artifact '{filename}'.")
                # Extract and return the raw byte content
                pdf_bytes = pdf_artifact.inline_data.data
                return pdf_bytes
            else:
                raise ValueError(
                    f"Artifact '{filename}' is not a PDF or Image. "
                    f"Found type: '{pdf_artifact.inline_data.mime_type}'."
                )
        else:
            raise ValueError(f"Artifact '{filename}' not found or is empty.")

    except ValueError as e:
        print(f"Error loading artifact: {e}")
        raise e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}")


async def save_structured_response(
    structured_response: str,
    file_name: str,
    tool_context: ToolContext,
    file_type: str = "csv",
) -> str:
    """
    Saves structured response (e.g. from Gemini w/ controlled generation)
    as JSON artifact in tool_context

    Args:
        structured_response: response from Gemini in text
        file_name: name of file to save (without ".csv" or ".json" in name)
        tool_context: context object provided by ADK framework containing user
          content

    Returns:
        A success message with the name & version of the CSV/JSON file saved as
          an artifact
    """

    file_name_with_ext = f"{file_name}.{file_type}"
    mime_type = "application/json"

    # Save the content as an artifact
    version = await tool_context.save_artifact(
        filename=f"{file_name_with_ext}",
        artifact=types.Part.from_bytes(
            data=structured_response.encode("utf-8"),
            mime_type=mime_type,
        ),
    )

    return f"Saved data to artifact {file_name_with_ext} w/ version {version}."


async def generate_data_from_pdf_and_schema(
    pdf_file_name: str,
    tool_context: ToolContext,
    output_file_name: str = "extracted_data",
):
    """Extracts data from PDF with specified schema

    Args:
        pdf_file_name: name of PDF file to read in
        tool_context: context object provided by ADK framework containing user
          content

    Returns:
        A success message with the name & version of the CSV/JSON file saved as
          an artifact
    """

    output_file_type = "json"

    # Use Pydantic model to generate the response schema
    # schema = ExtractionResult.model_json_schema()

    try:
        pdf_data = await get_pdf_from_artifact(pdf_file_name, tool_context)
    except ValueError as e:
        return str(e)

    if pdf_file_name.lower().endswith(".pdf"):
        document = types.Part.from_bytes(data=pdf_data, mime_type="application/pdf")
    else:
        extension = pdf_file_name.split(".")[-1]
        document = types.Part.from_bytes(data=pdf_data, mime_type=f"image/{extension}")

    contents = [types.Content(role="user", parts=[document])]

    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(
            thinking_budget=512,
        ),
        response_schema=ExtractionResult,
    )

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=contents,
        config=generate_content_config,
    )

    response_text = response.text.replace("\n", " ")

    # Validate with Pydantic
    try:
        extraction_data = ExtractionResult.model_validate_json(response_text)
        # Use the validated data (serialized back to JSON for storage)
        validated_json = extraction_data.model_dump_json(indent=2)
    except Exception as e:
        return f"Error: Extracted data failed Pydantic validation. {str(e)}"

    file_save_result = await save_structured_response(
        structured_response=validated_json,
        file_name=output_file_name,
        tool_context=tool_context,
        file_type=output_file_type,
    )

    return file_save_result


pdf_data_extraction_agent = Agent(
    name="pdf_data_extraction_agent",
    model=GEMINI_MODEL_ID,
    description="""
        Agent to extract data from provided PDF into structured format
        """,
    instruction="""
        When a PDF or Image file is uploaded, use generate_data_from_pdf_and_schema tool to extract the data into JSON format.
        Name the output file using the original input file name as much as possible.

        Extraction guidelines:
        - Extract all line items individually. Do not merge or summarize.
        - For service line items (rides, deliveries, calls, data plans, etc.), use the
          `notes` field to capture any structured details not covered by other fields.
          Example for a rideshare line item:
            {
              "description": "UberX trip",
              "total": 8.50,
              "notes": "Origin: Palermo, Buenos Aires. Destination: Retiro. Distance: 4.2 km. Duration: 18 min."
            }
        - Only populate `notes` when there is meaningful supplementary information
          not already captured in other fields. Leave it null otherwise.
        - Use ISO 8601 format (YYYY-MM-DD) for all dates.
        - All monetary values must be numbers, not strings.

        Once the relevant data has been extracted, let the user know the name of
        the resulting file (including version) and that it should be
        available in the 'Artifacts' pane in adk web. If there's an error in
        data extraction or JSON creation, let the user know what it was.
    """,
    output_key="data_extraction_agent_output",
    tools=[generate_data_from_pdf_and_schema],
)

root_agent = pdf_data_extraction_agent

app = App(
    name="pdf_data_extraction_agent",
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()],
)
