from typing import Any, Dict, List

def lc_tool_to_openai_def(tool) -> Dict[str, Any]:
    """
    Convert a LangChain StructuredTool into an OpenAI / Groq tool definition.
    """
    # args_schema is a Pydantic BaseModel; use its JSON schema
    # LangChain v0.2/0.3: model_json_schema(); older: schema()
    # print(tool.args_schema)
    # print(type(tool.args_schema))
    # print(tool.args_schema['properties'])

    # if hasattr(tool.args_schema, "model_json_schema"):
    #     params_schema = tool.args_schema.model_json_schema()
    # else:
    #     params_schema = tool.args_schema.schema()

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.args_schema or "",
            "properties": tool.args_schema['properties'] or "",
        },
    }

def build_tool_mapping(tools, tool_defs):
    """
    Create a mapping from tool name → callable executor.
    This allows you to quickly execute a tool when the model requests it.
    """
    mapping = {}
    for tool, tool_def in zip(tools, tool_defs):
        name = tool_def["function"]["name"]
        mapping[name] = tool   # Each 'tool' is a LangChain StructuredTool object
    return mapping

