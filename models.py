from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class Tool(BaseModel):
    name: str = Field(description="Name of the tool")
    description: str = Field(description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(description="Parameters required by the tool")

class ToolSelection(BaseModel):
    tool_name: Optional[str] = Field(description="Name of the selected tool, or None if no tool is needed")
    reason: str = Field(description="Reason for selecting or not selecting a tool")
    parameters: Optional[Dict[str, Any]] = Field(description="Parameters to pass to the tool if selected")

class ToolResult(BaseModel):
    """Model for tool execution results"""
    success: bool = Field(description="Whether the tool execution was successful")
    tool_name: Optional[str] = Field(description="Name of the tool that was used", default=None)
    parameters: Optional[Dict[str, Any]] = Field(description="Parameters used for the tool", default=None)
    results: Optional[Any] = Field(description="Results returned by the tool", default=None)
    error: Optional[str] = Field(description="Error message if tool execution failed", default=None)

class BakedResponse(BaseModel):
    """Model for AI-generated responses"""
    thoughts: str = Field(description="Thoughts about the user's request")
    response: str = Field(description="Natural language response to the user")
    references: Optional[List[str]] = Field(description="List of references or sources used if a tool was used", default=None) 