import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin
from google.adk.tools import ToolContext
from google.genai import types

from pdf_data_extraction_agent.extractors.generic import GENERIC_STRATEGY
from pdf_data_extraction_agent.extractors.registry import get_strategy
from pdf_data_extraction_agent.pipeline.extract import _call_gemini

load_dotenv()

_MODEL_ID = os.getenv("GEMINI_MODEL_ID") or os.getenv("MODEL_ID", "gemini-2.5-flash")


async def get_pdf_from_artifact(filename: str, tool_context: ToolContext) -> tuple[bytes, str]:
    """
    Loads a specific PDF or image from saved artifacts and returns its byte content and mime type.

    Args:
        filename: Name of PDF artifact file to load
        tool_context: context object provided by ADK framework

    Returns:
        Tuple of (byte content, mime_type)

    Raises:
        ValueError: If the artifact is not found or is not a PDF/image
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
                return pdf_artifact.inline_data.data, pdf_artifact.inline_data.mime_type
            elif pdf_artifact.inline_data.mime_type.startswith("image/"):
                print(f"Successfully loaded Image artifact '{filename}'.")
                return pdf_artifact.inline_data.data, pdf_artifact.inline_data.mime_type
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
    file_type: str = "json",
) -> str:
    """
    Saves structured response as JSON artifact in tool_context

    Args:
        structured_response: response from Gemini in text
        file_name: name of file to save (without extension)
        tool_context: context object provided by ADK framework containing user content

    Returns:
        A success message with the name & version of the file saved as an artifact
    """
    file_name_with_ext = f"{file_name}.{file_type}"

    version = await tool_context.save_artifact(
        filename=file_name_with_ext,
        artifact=types.Part.from_bytes(
            data=structured_response.encode("utf-8"),
            mime_type="application/json",
        ),
    )

    return f"Saved data to artifact {file_name_with_ext} w/ version {version}."


async def generate_data_from_pdf_and_schema(
    pdf_file_name: str,
    tool_context: ToolContext,
    output_file_name: str = "extracted_data",
):
    """Extracts data from PDF or image with the new pipeline extraction logic.

    Args:
        pdf_file_name: name of PDF or image artifact file to read
        tool_context: context object provided by ADK framework containing user content
        output_file_name: name for the output JSON artifact (without extension)

    Returns:
        A success message with the name & version of the JSON file saved as an artifact
    """
    try:
        pdf_data, mime_type = await get_pdf_from_artifact(pdf_file_name, tool_context)
    except ValueError as e:
        return str(e)

    # Pass 1: generic extraction to detect issuer
    result, error, _ = _call_gemini(pdf_data, mime_type, GENERIC_STRATEGY)

    if result is None:
        return f"Extraction failed: {error}"

    # Pass 2: check for issuer-specific strategy
    issuer_name = result.issuer.name if result.issuer else None
    strategy = get_strategy(issuer_name)

    if strategy.name != GENERIC_STRATEGY.name:
        result2, _, _ = _call_gemini(pdf_data, mime_type, strategy)
        if result2 is not None:
            result = result2

    validated_json = result.model_dump_json(indent=2)

    return await save_structured_response(
        structured_response=validated_json,
        file_name=output_file_name,
        tool_context=tool_context,
    )


root_agent = Agent(
    name="pdf_data_extraction_agent",
    model=_MODEL_ID,
    description="Extract structured financial data from uploaded PDF/image documents.",
    instruction="""
        You are a document data extraction assistant.

        When the user uploads a file, call generate_data_from_pdf_and_schema with the filename.
        Name the output file using the original input file name as much as possible.

        Extraction guidelines:
        - Extract all line items individually. Do not merge or summarize.
        - For service line items (rides, deliveries, calls, data plans, etc.), use the
          `notes` field to capture any structured details not covered by other fields.
        - Use ISO 8601 format (YYYY-MM-DD) for all dates.
        - All monetary values must be numbers, not strings.

        After extraction, let the user know the name of the resulting file (including version)
        and that it should be available in the 'Artifacts' pane in adk web.
        If there's an error in data extraction or JSON creation, let the user know what it was.
    """,
    tools=[generate_data_from_pdf_and_schema],
)

app = App(
    name="pdf_data_extraction_agent",
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()],
)