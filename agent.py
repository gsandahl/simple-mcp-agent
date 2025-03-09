from typing import List, Dict, Any
from opperai import AsyncOpper
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import subprocess
import os
from models import Tool, ToolSelection, ToolResult, BakedResponse

class MCPAgent:
    def __init__(self):
        """Initialize the agent"""
        self.opper = AsyncOpper()
        self.tools: List[Tool] = []
        self.sessions: List[Dict[str, Any]] = []  # Store both client and session
        
    def _get_docker_path(self):
        """Helper to find docker executable path"""
        try:
            result = subprocess.run(['which', 'docker'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            try:
                result = subprocess.run(['where', 'docker'], capture_output=True, text=True, check=True)
                return result.stdout.strip().split('\n')[0]
            except subprocess.CalledProcessError:
                return "docker"

    async def connect_to_server(self, server_config: Dict[str, Any]):
        """Connect to an MCP server and retrieve its tools"""
        docker_path = self._get_docker_path()
        
        # Set up server parameters based on config
        server_params = StdioServerParameters(
            command=docker_path,
            args=[
                "run", "-i", "--rm",
                *[item for pair in server_config.get("env", {}).items() 
                  for item in ("-e", f"{pair[0]}={pair[1]}")],
                server_config["image"]
            ],
            env=os.environ.copy()
        )

        # Connect to server
        client = stdio_client(server_params)
        read, write = await client.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        
        # Store both client and session for cleanup
        self.sessions.append({
            "client": client,
            "session": session
        })
        
        # Get available tools from server
        tools = await session.list_tools()        
        # Convert MCP tools to our Tool format
        for tool in tools.tools:
            self.tools.append(tool)

    async def cleanup(self):
        """Cleanup all sessions properly"""
        for connection in self.sessions:
            session = connection["session"]
            client = connection["client"]
            
            try:
                await session.__aexit__(None, None, None)
                await client.__aexit__(None, None, None)
            except Exception:
                pass  # Best effort cleanup

    async def initialize(self, server_configs: List[Dict[str, Any]]):
        """Initialize connections to all configured MCP servers"""
        for config in server_configs:
            await self.connect_to_server(config)

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the selected tool with given parameters"""
        # Find the session that has this tool
        for connection in self.sessions:
            try:
                result = await connection["session"].call_tool(tool_name, parameters)
                return {
                    "success": True,
                    "results": result.content if hasattr(result, 'content') else result,
                    "message": f"Successfully executed {tool_name}"
                }
            except Exception:
                continue
                
        return {
            "success": False,
            "message": f"No server found with tool: {tool_name}"
        }

    async def process_input(self, user_input: str) -> ToolResult:
        """Process user input and execute appropriate tool if needed"""
        
        tool_selection, _ = await self.opper.call(
            name="select_tool",
            instructions="""
            Based on the user input and available tools, determine if a tool should be used.
            If a tool is needed, select the most appropriate one and provide the necessary parameters.
            If no tool is needed, return None for tool_name and explain why.
            """,
            input={
                "user_input": user_input,
                "available_tools": [
                    {"name": tool.name, "description": tool.description}
                    for tool in self.tools
                ]
            },
            output_type=ToolSelection
        )

        if not tool_selection.tool_name:
            return ToolResult(
                success=True,
                error=tool_selection.reason
            )

        # Find the selected tool
        selected_tool = next(
            (tool for tool in self.tools if tool.name == tool_selection.tool_name),
            None
        )

        if not selected_tool:
            return ToolResult(
                success=False,
                error=f"Selected tool '{tool_selection.tool_name}' not found"
            )

        # Execute the tool
        tool_result = await self.execute_tool(
            selected_tool.name,
            tool_selection.parameters or {}
        )

        return ToolResult(
            success=tool_result["success"],
            tool_name=selected_tool.name,
            parameters=tool_selection.parameters,
            results=tool_result.get("results"),
            error=None if tool_result["success"] else tool_result.get("message")
        )

async def bake_response(opper: AsyncOpper, user_input: str, tool_result: ToolResult) -> BakedResponse:
    """
    Generate a natural language response based on user input and tool results
    """
    response, _ = await opper.call(
        name="bake_response",
        instructions="""
        Generate a natural, helpful response to the user's input.
        If tool results are provided and successful:
        1. Incorporate the tool results into a clear, concise response
        2. Add relevant sources/URLs as references
        If tool failed or wasn't needed:
        1. Provide a direct response explaining why
        Always maintain a helpful, conversational tone.
        """,
        input={
            "user_input": user_input,
            "tool_result": tool_result.dict()
        },
        output_type=BakedResponse
    )

    return response 