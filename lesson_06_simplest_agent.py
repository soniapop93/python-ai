import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

class FileNameValidator(BaseModel):
    name: str = Field(description="Name of the text file in this project")

class FileSummaryValidator(BaseModel):
    """This validator can validate the output of an agent, the JSON returned by the summary agent"""

    title: str = Field(description="The generated title for the file")
    summary: str = Field(description="The summary for that file")

def summarize_file(client: OpenAI, args: dict):
    # Will receive a file name, will read the file, provide it to an agent, and return a summary
    try:
        req = FileNameValidator.model_validate(args)
        filename = req.name
        path = Path(filename).resolve()
        path.relative_to(Path.cwd().resolve())
        text = path.read_text()

        response = client.chat.completions.create(
            model=os.getenv("OPEN_ROUTER_MODEL_NAME"),
            messages=[
                {"role": "system", "content": "Return ONLy JSON, that contains a title and a short summary. Summarise the file you received and put it in the JSON response"},
                {"role": "user", "content": f"Please summarise this file for me: {text}"}],
            response_format={
                "type": "json_schema",
                "strict": True,
                "json_schema": {"name":"file_summary", "schema": FileSummaryValidator.model_json_schema()}}
        ).choices[0].message

        validated_model_json = FileSummaryValidator.model_validate_json(response.content)

        return validated_model_json.model_dump_json()

    except Exception as exc:
        return f"error: {exc}"

def run_tests() -> str:
    try:
        result = subprocess.run(
            ["uv", "run", "pytest"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=60
        )
        return (result.stdout or "No output") + "" + (result.stderr or "")
    except Exception as e:
        print(e)

def complete(client: OpenAI, messages: list[dict], tools: list[dict]):
    response = client.chat.completions.create(
        messages=messages,
        model=os.getenv("OPEN_ROUTER_MODEL_NAME"),
        tools=tools,
        tool_choice="auto"
    ).choices[0].message
    return response


def main():
    load_dotenv()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPEN_ROUTER_API_KEY")
    )

    messages = []
    messages.append({
        "role": "system",
        "content": "You are a helpful assistant. If the user asks to run some tests, please only run the run_tests tool that you have at your disposal. if instead the user asks to summarize a file use the provided summarize_file tool that you have."
    })

    while True:
        inp = input("you> ")

        if inp == "quit":
            break
        messages.append({
            "role": "user",
            "content": input("you> ")
        })

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_tests",
                    "description": "Run uv run pytest"
                }
            }
        ]

        response = complete(client, messages, tools)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                if tool_name == "summarize_file":
                    args = tool_call.function.arguments
                    output = summarize_file(client, args)
                if tool_name == "run_tests":
                    output = run_tests()
                    messages.append(
                        {
                            "role": "system",
                            "tool_call_id": tool_call.tool_call_id,
                            "content": output
                        }
                    )

            response = complete(client, messages, tools)
            print("agent> ", response)

        print(f"Message count: {len(messages)}")

if __name__ == "__main__":
    # main()
    # print(run_tests())
    load_dotenv()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPEN_ROUTER_API_KEY")
    )
    print(summarize_file(client, args={"name":"lesson_06_simplest_agent.py"}))
