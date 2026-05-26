from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .handlers import handle_load

app = Server("chassis")


@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="chassis/load",
            description="Load chassis instruction components matching the current context",
            arguments=[
                types.PromptArgument(
                    name="prompt",
                    description="The user's message to match components against",
                    required=True,
                )
            ],
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> types.GetPromptResult:
    if name != "chassis/load":
        raise ValueError(f"Unknown prompt: {name}")

    prompt_text = (arguments or {}).get("prompt", "")
    result = handle_load(prompt_text, project_root=Path.cwd())

    if result["type"] == "empty":
        content = "[chassis] No matching components for this context."
    else:
        content = result["text"]

    return types.GetPromptResult(
        description="Chassis component instructions",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=content),
            )
        ],
    )


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="chassis_load_components",
            description="Load chassis instruction components for the current prompt. Call this when context has shifted and you need fresh instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The current user prompt to match components against",
                    }
                },
                "required": ["prompt"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "chassis_load_components":
        raise ValueError(f"Unknown tool: {name}")

    prompt = arguments.get("prompt", "")
    result = handle_load(prompt, project_root=Path.cwd())

    if result["type"] == "empty":
        text = "[chassis] No matching components for this context."
    else:
        text = result["text"]

    return [types.TextContent(type="text", text=text)]


def main() -> None:
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
