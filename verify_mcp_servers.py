import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server(script_path: str):
    # 1. Define how to start the MCP server
    server_params = StdioServerParameters(
        command="python",
        args=[script_path]
    )

    print(f"\n --- Testing {script_path} ---")

    # 2. Open the stdio connection
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 3. Initialize the protocol handshake
            await session.initialize()

            # 4. Ask the server what tools it exposes
            tools = await session.list_tools()
            print(" Discovered Tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # 5. Execute the tool dynamically with a test query
            if tools.tools:
                tool_name = tools.tools[0].name
                print(f" Executing '{tool_name}' with query='acme'...")
                result = await session.call_tool(tool_name, arguments={"query": "acme"})

                # Format and print the JSON response
                print(f" Result: {result.content[0].text}")


async def main():
    await test_server("mcp_servers/crm.py")
    await test_server("mcp_servers/billing.py")
    await test_server("mcp_servers/app_db.py")


if __name__ == "__main__":
    asyncio.run(main())
