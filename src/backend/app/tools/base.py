"""
Tools 系统基础
"""
import inspect
import json
from typing import Callable, Dict, Any, List, Optional, get_type_hints
from pydantic import BaseModel


class Tool:
    """工具类"""

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        self.is_async = inspect.iscoroutinefunction(func)
        self._schema = self._generate_schema()

    def _generate_schema(self) -> Dict[str, Any]:
        """从函数签名生成 JSON Schema"""
        sig = inspect.signature(self.func)
        hints = get_type_hints(self.func) if hasattr(self.func, '__annotations__') else {}

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'ctx', 'context'):
                continue

            param_type = hints.get(param_name, str)
            json_type = self._python_type_to_json(param_type)

            # 从 docstring 获取参数描述
            param_desc = self._extract_param_description(param_name)

            properties[param_name] = {
                "type": json_type,
                "description": param_desc
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _python_type_to_json(self, python_type) -> str:
        """Python 类型转 JSON Schema 类型"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(python_type, "string")

    def _extract_param_description(self, param_name: str) -> str:
        """从 docstring 提取参数描述"""
        if not self.func.__doc__:
            return ""

        lines = self.func.__doc__.split('\n')
        for i, line in enumerate(lines):
            if f'{param_name}:' in line or f'{param_name} :' in line:
                # 提取冒号后的描述
                parts = line.split(':', 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return ""

    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        if self.is_async:
            return await self.func(**kwargs)
        return self.func(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 LLM）"""
        # Extract first non-empty line as description
        description = ""
        if self.description:
            for line in self.description.split('\n'):
                line = line.strip()
                if line and not line.startswith('Args:'):
                    description = line
                    break
        return {
            "name": self.name,
            "description": description,
            "parameters": self._schema
        }


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Callable:
    """
    工具装饰器

    使用方式:
    @tool()
    def my_tool(param: str) -> str:
        '''工具描述'''
        return result

    或者:
    @tool(name="custom_name", description="自定义描述")
    def my_tool(param: str) -> str:
        return result
    """
    def decorator(func: Callable) -> Tool:
        return Tool(func, name=name, description=description)
    return decorator


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """注册函数为工具"""
        t = Tool(func, name, description)
        self.register(t)
        return t

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def remove(self, name: str):
        """移除工具"""
        if name in self._tools:
            del self._tools[name]

    def list_tools(self) -> List[str]:
        """列出所有工具名"""
        return list(self._tools.keys())

    def get_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict]:
        """获取工具 Schema 列表"""
        names = tool_names or list(self._tools.keys())
        return [
            self._tools[name].to_dict()
            for name in names
            if name in self._tools
        ]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return await tool.execute(**arguments)
