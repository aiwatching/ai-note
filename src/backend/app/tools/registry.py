"""
默认工具注册中心和内置工具
"""
from datetime import datetime
from .base import ToolRegistry, tool


# 全局默认注册中心
default_registry = ToolRegistry()


# ============ 内置工具 ============

@tool()
def get_current_time() -> str:
    """获取当前时间

    Returns:
        当前时间的字符串表示
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool()
def calculate(expression: str) -> str:
    """计算数学表达式

    Args:
        expression: 数学表达式，如 "2 + 3 * 4"

    Returns:
        计算结果
    """
    try:
        # 安全的数学计算
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            return "Error: 表达式包含不允许的字符"
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


# 注册内置工具
default_registry.register(get_current_time)
default_registry.register(calculate)
