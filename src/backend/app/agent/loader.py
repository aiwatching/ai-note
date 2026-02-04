"""
Agent Configuration Loader

Loads agent configurations from YAML frontmatter + Markdown files.
Follows OpenClaw-style skill configuration pattern.
"""
import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AgentRequirements:
    """Agent requirements for eligibility checks"""
    env: List[str] = field(default_factory=list)      # Required environment variables
    bins: List[str] = field(default_factory=list)     # Required binaries in PATH
    os: List[str] = field(default_factory=list)       # Supported operating systems
    config: List[str] = field(default_factory=list)   # Required config keys


@dataclass
class AgentConfig:
    """Agent configuration parsed from .md file"""
    # Basic info (from frontmatter)
    id: str
    name: str
    description: str
    provider: str
    emoji: str = ""

    # Requirements
    requires: Optional[AgentRequirements] = None

    # Behavior flags
    always: bool = False                    # Always available regardless of requirements
    user_invocable: bool = True             # Can be invoked via /command
    disable_model_invocation: bool = False  # Prevent auto-invocation by model

    # Tool and model config
    tool_profile: str = "full"              # Tool access profile
    primary_env: Optional[str] = None       # Primary environment variable
    task_model_mapping: Dict[str, str] = field(default_factory=dict)

    # Parsed from markdown body
    skills: List[Dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    tools: List[Dict[str, Any]] = field(default_factory=list)


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
    """
    if not content.startswith('---'):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3:end_match.start() + 3]
    remaining = content[end_match.end() + 3:]

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, remaining


def parse_requirements(raw: Any) -> Optional[AgentRequirements]:
    """Parse requirements from frontmatter"""
    if not raw or not isinstance(raw, dict):
        return None

    return AgentRequirements(
        env=_normalize_list(raw.get('env')),
        bins=_normalize_list(raw.get('bins')),
        os=_normalize_list(raw.get('os')),
        config=_normalize_list(raw.get('config')),
    )


def _normalize_list(value: Any) -> List[str]:
    """Normalize a value to a list of strings"""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, str):
        return [s.strip() for s in value.split(',') if s.strip()]
    return []


def parse_skills_section(content: str) -> List[Dict[str, Any]]:
    """Parse ## Skills section from markdown body"""
    skills = []

    # Find Skills section
    skills_match = re.search(r'## Skills\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not skills_match:
        return skills

    skills_content = skills_match.group(1)

    # Parse each ### Skill
    skill_pattern = r'### (.+?)\n(.*?)(?=\n### |\n## |\Z)'
    for match in re.finditer(skill_pattern, skills_content, re.DOTALL):
        skill_name = match.group(1).strip()
        skill_body = match.group(2).strip()

        # Extract description (text before **Examples:**)
        desc_match = re.search(r'^(.*?)(?=\*\*Examples:\*\*|\Z)', skill_body, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else skill_body

        # Extract examples
        examples = []
        examples_match = re.search(r'\*\*Examples:\*\*\s*\n(.*?)(?=\n### |\n## |\Z)', skill_body, re.DOTALL)
        if examples_match:
            for line in examples_match.group(1).split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    # Remove quotes and clean up
                    example = line[2:].strip().strip('"\'')
                    if example:
                        examples.append(example)

        skills.append({
            'name': skill_name,
            'description': description,
            'examples': examples,
        })

    return skills


def parse_tools_section(content: str) -> List[Dict[str, Any]]:
    """Parse ## Tools section from markdown body"""
    tools = []

    # Find Tools section
    tools_match = re.search(r'## Tools\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not tools_match:
        return tools

    tools_content = tools_match.group(1)

    # Parse each ### Tool
    tool_pattern = r'### (\w+)\s*\n(.*?)(?=\n### |\n## |\Z)'
    for match in re.finditer(tool_pattern, tools_content, re.DOTALL):
        tool_name = match.group(1).strip()
        tool_body = match.group(2).strip()

        # First line is description
        lines = tool_body.split('\n')
        description = lines[0].strip() if lines else ""

        # Parse parameters
        parameters = []
        params_match = re.search(r'\*\*Parameters:\*\*\s*\n(.*?)(?=\*\*Returns:\*\*|\n### |\n## |\Z)',
                                  tool_body, re.DOTALL)
        if params_match:
            param_pattern = r'- (\w+) \(([^)]+)\)(?::\s*(.+))?'
            for param_match in re.finditer(param_pattern, params_match.group(1)):
                param_name = param_match.group(1)
                param_type = param_match.group(2)
                param_desc = param_match.group(3).strip() if param_match.group(3) else ""

                # Check if optional
                is_optional = 'optional' in param_type.lower()
                base_type = re.sub(r',?\s*optional', '', param_type, flags=re.IGNORECASE).strip()

                parameters.append({
                    'name': param_name,
                    'type': base_type,
                    'description': param_desc,
                    'optional': is_optional,
                })

        # Parse returns
        returns = None
        returns_match = re.search(r'\*\*Returns:\*\*\s*\n(.*?)(?=\n### |\n## |\Z)', tool_body, re.DOTALL)
        if returns_match:
            returns = returns_match.group(1).strip()

        tools.append({
            'name': tool_name,
            'description': description,
            'parameters': parameters,
            'returns': returns,
        })

    return tools


def parse_system_prompt(content: str) -> str:
    """
    Extract system prompt from markdown body.
    Everything before ## Skills or ## Tools is the system prompt.

    Also injects current date information at the beginning.
    """
    from datetime import datetime

    # Remove the title (# Title)
    content = re.sub(r'^#\s+[^\n]+\n', '', content.strip())

    # Find where Skills or Tools section starts
    end_match = re.search(r'\n## (Skills|Tools)\s*\n', content)
    if end_match:
        prompt = content[:end_match.start()].strip()
    else:
        prompt = content.strip()

    # Inject current date at the beginning
    current_date = datetime.now().strftime("%Y年%m月%d日")
    current_year = datetime.now().year

    date_context = f"""**当前日期**: {current_date}

**重要**: 搜索和分析信息时：
- 使用当前年份 ({current_year} 年)
- 财报、新闻等应搜索最新数据
- 不要引用过时信息

---

"""

    return date_context + prompt


def parse_agent_md(content: str) -> AgentConfig:
    """
    Parse agent configuration from YAML frontmatter + Markdown file.

    Format:
    ---
    id: agent-id
    name: Agent Name
    description: Agent description
    provider: deepseek
    requires:
      env: [API_KEY]
      bins: [some-cli]
    tool-profile: coding
    ---

    # Agent Title

    System prompt content here...

    ## Skills
    ### Skill Name
    Skill description

    ## Tools
    ### tool_name
    Tool description
    """
    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)

    # Extract basic info
    agent_id = frontmatter.get('id', 'unknown')
    name = frontmatter.get('name', 'Unknown Agent')
    description = frontmatter.get('description', '')
    provider = frontmatter.get('provider', 'deepseek')
    emoji = frontmatter.get('emoji', '')

    # Parse requirements
    requires = parse_requirements(frontmatter.get('requires'))

    # Parse behavior flags
    always = frontmatter.get('always', False)
    user_invocable = frontmatter.get('user-invocable', True)
    disable_model_invocation = frontmatter.get('disable-model-invocation', False)

    # Parse tool/model config
    tool_profile = frontmatter.get('tool-profile', 'full')
    primary_env = frontmatter.get('primary-env')
    task_model_mapping = frontmatter.get('task-model-mapping', {})

    # Parse markdown body
    skills = parse_skills_section(body)
    tools = parse_tools_section(body)
    system_prompt = parse_system_prompt(body)

    return AgentConfig(
        id=agent_id,
        name=name,
        description=description,
        provider=provider,
        emoji=emoji,
        requires=requires,
        always=always,
        user_invocable=user_invocable,
        disable_model_invocation=disable_model_invocation,
        tool_profile=tool_profile,
        primary_env=primary_env,
        task_model_mapping=task_model_mapping,
        skills=skills,
        system_prompt=system_prompt,
        tools=tools,
    )


def check_requirements(requires: Optional[AgentRequirements]) -> tuple[bool, List[str]]:
    """
    Check if agent requirements are met.

    Returns:
        Tuple of (is_eligible, missing_items)
    """
    if not requires:
        return True, []

    missing = []

    # Check environment variables
    for env_var in requires.env:
        if not os.environ.get(env_var):
            missing.append(f"env:{env_var}")

    # Check binaries
    import shutil
    for binary in requires.bins:
        if not shutil.which(binary):
            missing.append(f"bin:{binary}")

    # Check OS
    if requires.os:
        import platform
        current_os = platform.system().lower()
        os_map = {'darwin': 'darwin', 'linux': 'linux', 'windows': 'win32'}
        current_normalized = os_map.get(current_os, current_os)
        if current_normalized not in [o.lower() for o in requires.os]:
            missing.append(f"os:{current_os} (requires: {', '.join(requires.os)})")

    return len(missing) == 0, missing


def load_agent_configs(
    configs_dir: Optional[Path] = None,
    check_eligibility: bool = True,
) -> List[AgentConfig]:
    """
    Load all agent configurations from directory.

    Args:
        configs_dir: Directory containing .md config files
        check_eligibility: Whether to check requirements and filter ineligible agents

    Returns:
        List of AgentConfig objects
    """
    if configs_dir is None:
        configs_dir = Path(__file__).parent / "configs"

    configs = []

    for md_file in sorted(configs_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding='utf-8')
            config = parse_agent_md(content)

            # Check eligibility
            if check_eligibility and not config.always:
                eligible, missing = check_requirements(config.requires)
                if not eligible:
                    print(f"[Agent Loader] Skipped {config.name} ({config.id}) - missing: {', '.join(missing)}")
                    continue

            configs.append(config)
            emoji = f"{config.emoji} " if config.emoji else ""
            print(f"[Agent Loader] Loaded: {emoji}{config.name} ({config.id}) [provider={config.provider}]")

        except Exception as e:
            print(f"[Agent Loader] Error loading {md_file.name}: {e}")

    return configs


def get_agent_config(
    agent_id: str,
    configs_dir: Optional[Path] = None,
    check_eligibility: bool = True,
) -> Optional[AgentConfig]:
    """
    Get a specific agent configuration by ID.

    Args:
        agent_id: Agent ID to find
        configs_dir: Directory containing .md config files
        check_eligibility: Whether to check requirements

    Returns:
        AgentConfig or None if not found
    """
    configs = load_agent_configs(configs_dir, check_eligibility)
    for config in configs:
        if config.id == agent_id:
            return config
    return None


def get_eligible_agents(configs_dir: Optional[Path] = None) -> List[AgentConfig]:
    """Get all agents that pass eligibility checks"""
    return load_agent_configs(configs_dir, check_eligibility=True)


def get_all_agents(configs_dir: Optional[Path] = None) -> List[AgentConfig]:
    """Get all agents regardless of eligibility"""
    return load_agent_configs(configs_dir, check_eligibility=False)


def get_user_invocable_agents(configs_dir: Optional[Path] = None) -> List[AgentConfig]:
    """Get agents that can be invoked via user commands"""
    configs = load_agent_configs(configs_dir, check_eligibility=True)
    return [c for c in configs if c.user_invocable]


def get_model_invocable_agents(configs_dir: Optional[Path] = None) -> List[AgentConfig]:
    """Get agents that can be auto-invoked by the model"""
    configs = load_agent_configs(configs_dir, check_eligibility=True)
    return [c for c in configs if not c.disable_model_invocation]
