import asyncio
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

# Add parent directory to path for script execution
from agent import MCPAgent, bake_response
# If needed: from schemas import BakedResponse, Tool, ToolResult

async def main():
    # Initialize Rich console
    console = Console()
    
    # Configure MCP servers with their tools
    server_configs = [
        {
            "image": "mcp/brave-search:latest",
            "env": {
                "BRAVE_API_KEY": "BSAXWy-jdRW5ihB9-cUFtvD48enYxtQ"
            }
        }
    ]

    # Initialize the agent with server configs
    agent = MCPAgent()
    try:
        console.print(Panel.fit("Initializing MCP Agent...", border_style="blue"))
        await agent.initialize(server_configs)

        console.print(Panel.fit("MCP Agent initialized. Type '[bold red]quit[/bold red]' to exit.", border_style="green"))
        
        # Display available tools in a table
        if agent.tools:
            table = Table(title="Available Tools")
            table.add_column("Tool Name", style="cyan")
            table.add_column("Description", style="green")
            
            for tool in agent.tools:
                table.add_row(tool.name, tool.description)
            
            console.print(table)
        else:
            console.print("[yellow]No tools available[/yellow]")

        while True:
            user_input = console.input("\n[bold blue]You:[/bold blue] ").strip()
            
            if user_input.lower() in ('quit', 'exit', 'q'):
                console.print("[bold green]Goodbye![/bold green]")
                break
                
            if not user_input:
                continue
            
            with console.status("[bold green]Processing your request...[/bold green]"):
                # Process the input to get tool results
                tool_result = await agent.process_input(user_input)
                
                # Bake the response separately
                baked = await bake_response(agent.opper, user_input, tool_result)
            
            # Display the response in a panel
            console.print(Panel(baked.response, title="Agent Response", border_style="green"))
            
            # Display references if available
            if baked.references:
                ref_table = Table(title="Sources")
                ref_table.add_column("References", style="dim")
                
                for ref in baked.references:
                    ref_table.add_row(ref)
                
                console.print(ref_table)
                
    finally:
        # Ensure cleanup happens
        await agent.cleanup()

# Only run when executed as a script
if __name__ == "__main__":
    asyncio.run(main()) 