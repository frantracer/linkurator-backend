import asyncio
import json
import sys

import openai
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from linkurator_core.infrastructure.config.env_settings import EnvSettings


class MCPClient:
    def __init__(self, session: ClientSession, api_key: str) -> None:
        self.session: ClientSession = session
        self.api_key: str = api_key

    async def connect_to_server(self) -> None:
        """
        Connect to an MCP server
        """
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [
            {
                "role": "user",
                "content": query,
            },
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema,
        } for tool in response.tools]

        # OpenAI function calling
        functions = available_tools if available_tools else None
        final_text = []

        client = openai.AsyncOpenAI(api_key=self.api_key)

        openai_response = await client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            tools=functions,
            tool_choice="auto",
            max_completion_tokens=1000,
        )
        choice = openai_response.choices[0]
        message = choice.message
        if message.content:
            final_text.append(message.content)
        if message.function_call:
            tool_name = message.function_call.name
            tool_args = dict(json.loads(message.function_call.arguments))

            print(f"\nTool call detected: {tool_name} with args {tool_args}")

            # Execute tool call
            result = await self.session.call_tool(tool_name, tool_args)
            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": message.content if message.content else ""})
            messages.append({"role": "user", "content": result.content})

            # Get next response from OpenAI
            openai_response = client.chat.completions.create(
                model="o4-mini",
                messages=messages,
                max_completion_tokens=1000,
            )
            next_message = openai_response.choices[0].message
            if next_message.content:
                final_text.append(next_message.content)

        return "\n".join(final_text)

    async def chat_loop(self) -> None:
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {e!s}")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <path_to_server_script>")
        sys.exit(1)

    settings = EnvSettings()

    async with streamablehttp_client(f"{sys.argv[1]}/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            # Create an MCPClient instance
            client = MCPClient(session=session, api_key=settings.OPENAI_API_KEY)

            # Connect to the server
            await client.connect_to_server()

            # Start the chat loop
            await client.chat_loop()


if __name__ == "__main__":
    asyncio.run(main())
