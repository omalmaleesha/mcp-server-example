import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack
from dotenv import load_dotenv
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from groq import Groq

load_dotenv()  # Load environment variables from .env


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.groq = Groq()  # Requires GROQ_API_KEY in environment

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process query using Groq AI and MCP tools"""
        messages = [
            {"role": "user", "content": query}
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]

        # Initial Groq call
        response = self.groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Or "llama3-70b-8192"
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            max_tokens=1000,
        )

        final_text = []
        while True:
            choice = response.choices[0]
            message = choice.message

            if message.content:
                final_text.append(message.content)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    result = await self.session.call_tool(tool_name, tool_args)

                    messages.append({"role": "assistant", "tool_call_id": tool_call.id, "content": None})


                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(getattr(result, "content", ""))})

                # Continue loop with new response
                response = self.groq.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto",
                    max_tokens=1000,
                )
            else:
                break

        return "\n".join(final_text)

    async def chat_loop(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
