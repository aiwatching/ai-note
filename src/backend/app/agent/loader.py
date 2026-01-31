"""
Agent 配置加载器

从 .md 文件加载 Agent 配置
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    name: str
    description: str
    provider: str
    skills: List[Dict[str, str]]
    system_prompt: str
    tools: List[Dict[str, Any]]


def parse_agent_md(content: str) -> AgentConfig:
    """
    解析 Agent 配置 markdown 文件

    格式约定:
    - ## 基本信息 下的列表项包含 ID, Name, Description, Provider
    - ## Skills 下的 ### 标题为技能名，下面段落为描述
    - ## System Prompt 下的内容为系统提示
    - ## Tools 下的 ### 标题为工具名
    """

    # 解析基本信息
    id_match = re.search(r'\*\*ID\*\*:\s*(\w+)', content)
    name_match = re.search(r'\*\*Name\*\*:\s*(.+)', content)
    desc_match = re.search(r'\*\*Description\*\*:\s*(.+)', content)
    provider_match = re.search(r'\*\*Provider\*\*:\s*(\w+)', content)

    agent_id = id_match.group(1) if id_match else "unknown"
    name = name_match.group(1).strip() if name_match else "Unknown Agent"
    description = desc_match.group(1).strip() if desc_match else ""
    provider = provider_match.group(1) if provider_match else "deepseek"

    # 解析 Skills
    skills = []
    skills_section = re.search(r'## Skills\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if skills_section:
        skill_matches = re.findall(r'### (.+?)\n(.+?)(?=\n### |\n## |\Z)',
                                   skills_section.group(1), re.DOTALL)
        for skill_name, skill_desc in skill_matches:
            skills.append({
                "name": skill_name.strip(),
                "description": skill_desc.strip()
            })

    # 解析 System Prompt
    system_prompt = ""
    prompt_section = re.search(r'## System Prompt\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if prompt_section:
        system_prompt = prompt_section.group(1).strip()

    # 解析 Tools (仅记录工具名和描述，实际实现在代码中)
    tools = []
    tools_section = re.search(r'## Tools\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if tools_section:
        tool_matches = re.findall(r'### (\w+)\s*\n(.+?)(?=\n### |\n## |\Z)',
                                  tools_section.group(1), re.DOTALL)
        for tool_name, tool_content in tool_matches:
            # 解析工具描述（第一行）
            lines = tool_content.strip().split('\n')
            tool_desc = lines[0] if lines else ""

            # 解析参数
            params = []
            param_matches = re.findall(r'- (\w+) \((\w+)\):\s*(.+)', tool_content)
            for param_name, param_type, param_desc in param_matches:
                params.append({
                    "name": param_name,
                    "type": param_type,
                    "description": param_desc
                })

            tools.append({
                "name": tool_name,
                "description": tool_desc,
                "parameters": params
            })

    return AgentConfig(
        id=agent_id,
        name=name,
        description=description,
        provider=provider,
        skills=skills,
        system_prompt=system_prompt,
        tools=tools
    )


def load_agent_configs(configs_dir: Optional[Path] = None) -> List[AgentConfig]:
    """
    加载所有 Agent 配置

    Args:
        configs_dir: Agent 配置目录，默认为 agent/configs/

    Returns:
        AgentConfig 列表
    """
    if configs_dir is None:
        configs_dir = Path(__file__).parent / "configs"

    configs = []
    for md_file in configs_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
            config = parse_agent_md(content)
            configs.append(config)
            print(f"[Agent Loader] Loaded: {config.name} ({config.id})")
        except Exception as e:
            print(f"[Agent Loader] Error loading {md_file.name}: {e}")

    return configs


def get_agent_config(agent_id: str, configs_dir: Optional[Path] = None) -> Optional[AgentConfig]:
    """
    获取指定 Agent 的配置

    Args:
        agent_id: Agent ID
        configs_dir: Agent 配置目录

    Returns:
        AgentConfig 或 None
    """
    configs = load_agent_configs(configs_dir)
    for config in configs:
        if config.id == agent_id:
            return config
    return None
