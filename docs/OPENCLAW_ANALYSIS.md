# OpenClaw 项目深度分析

> 基于源代码的详细分析，重点关注 Agent 架构和 Skill 系统

## 1. 项目概览

OpenClaw 是一个复杂的个人 AI 助手框架，核心是基于 `pi-coding-agent` 的嵌入式 Agent 运行时。

### 核心目录结构

```
openclaw/
├── src/
│   ├── agents/                    # Agent 核心 (297 个文件!)
│   │   ├── pi-embedded-runner/    # Agent 执行引擎
│   │   ├── skills/                # Skill 加载系统
│   │   ├── tools/                 # 工具实现
│   │   ├── auth-profiles/         # 多账户认证
│   │   ├── model-*.ts             # 模型管理
│   │   ├── tool-policy.ts         # 工具策略
│   │   └── system-prompt.ts       # 系统提示构建
│   ├── config/                    # 配置系统
│   ├── channels/                  # 消息渠道 (Telegram, Discord 等)
│   └── plugins/                   # 插件系统
├── skills/                        # 50+ 技能定义
│   ├── github/SKILL.md
│   ├── notion/SKILL.md
│   ├── coding-agent/SKILL.md
│   └── ...
└── extensions/                    # 30+ 扩展插件
```

---

## 2. Skill 系统 (重点)

### 2.1 Skill 文件格式

每个 Skill 是一个 **YAML frontmatter + Markdown** 文件：

```yaml
---
name: github
description: "使用 gh CLI 与 GitHub 交互"
metadata:
  {
    "openclaw":
      {
        "emoji": "🐙",
        "requires": { "bins": ["gh"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "gh",
              "bins": ["gh"],
              "label": "通过 brew 安装 GitHub CLI",
            },
          ],
      },
  }
---

# GitHub Skill

使用说明...
```

### 2.2 Frontmatter 解析 (frontmatter.ts)

```typescript
// src/agents/skills/frontmatter.ts

export function resolveOpenClawMetadata(
  frontmatter: ParsedSkillFrontmatter,
): OpenClawSkillMetadata | undefined {
  // 解析 metadata.openclaw 字段
  return {
    always: boolean,           // 是否总是加载
    emoji: string,             // 显示图标
    homepage: string,          // 主页链接
    skillKey: string,          // 技能唯一标识
    primaryEnv: string,        // 主要环境变量
    os: string[],              // 支持的操作系统
    requires: {
      bins: string[],          // 必需的二进制
      anyBins: string[],       // 任一即可
      env: string[],           // 必需的环境变量
      config: string[],        // 必需的配置
    },
    install: SkillInstallSpec[], // 安装方式
  };
}
```

### 2.3 Skill 加载机制 (workspace.ts)

**三层优先级加载**：

```typescript
// src/agents/skills/workspace.ts

function loadSkillEntries(workspaceDir: string, opts?) {
  const bundledSkills = loadSkills({ dir: bundledSkillsDir, source: "openclaw-bundled" });
  const managedSkills = loadSkills({ dir: managedSkillsDir, source: "openclaw-managed" });
  const workspaceSkills = loadSkills({ dir: workspaceSkillsDir, source: "openclaw-workspace" });

  // 合并优先级: extra < bundled < managed < workspace
  const merged = new Map<string, Skill>();
  for (const skill of extraSkills) merged.set(skill.name, skill);
  for (const skill of bundledSkills) merged.set(skill.name, skill);
  for (const skill of managedSkills) merged.set(skill.name, skill);
  for (const skill of workspaceSkills) merged.set(skill.name, skill);  // 最高优先级

  return merged;
}
```

**加载位置**：
- `bundled`: `dist/skills/` (内置)
- `managed`: `~/.openclaw/skills/` (用户安装)
- `workspace`: `<workspace>/skills/` (项目级，**最高优先级**)

### 2.4 Skill 资格检查

```typescript
// src/agents/skills/config.ts

export function shouldIncludeSkill(params: {
  entry: SkillEntry;
  config?: OpenClawConfig;
  eligibility?: SkillEligibilityContext;
}): boolean {
  // 检查 OS 要求
  if (requires.os && !requires.os.includes(platform)) return false;

  // 检查二进制可用性
  if (requires.bins && !allBinsExist(requires.bins)) return false;

  // 检查环境变量
  if (requires.env && !allEnvsExist(requires.env)) return false;

  // 检查配置允许/禁止列表
  if (config.skills?.deny?.includes(name)) return false;
  if (config.skills?.allow && !config.skills.allow.includes(name)) return false;

  return true;
}
```

### 2.5 Skill 安装规格

```typescript
type SkillInstallSpec = {
  kind: "brew" | "node" | "go" | "uv" | "download";
  id?: string;           // 安装方式 ID
  label?: string;        // 显示标签
  bins?: string[];       // 安装后验证的二进制
  os?: string[];         // 仅在这些 OS 上可用

  // brew
  formula?: string;

  // node (npm/yarn/pnpm)
  package?: string;

  // go
  module?: string;

  // download
  url?: string;
  archive?: string;
  extract?: boolean;
  targetDir?: string;
};
```

### 2.6 实际 Skill 示例

**GitHub Skill** (`skills/github/SKILL.md`):
```yaml
---
name: github
description: "Interact with GitHub using the `gh` CLI..."
metadata:
  openclaw:
    emoji: "🐙"
    requires: { bins: ["gh"] }
    install:
      - id: brew
        kind: brew
        formula: gh
        bins: ["gh"]
        label: "Install GitHub CLI (brew)"
---
# GitHub Skill
Use the `gh` CLI to interact with GitHub...
```

**Notion Skill** (`skills/notion/SKILL.md`):
```yaml
---
name: notion
description: Notion API for creating and managing pages...
metadata:
  openclaw:
    emoji: "📝"
    requires: { env: ["NOTION_API_KEY"] }
    primaryEnv: "NOTION_API_KEY"
---
# Notion Skill
Use the Notion API...
```

**Coding Agent Skill** (`skills/coding-agent/SKILL.md`):
```yaml
---
name: coding-agent
description: Run Codex CLI, Claude Code, OpenCode...
metadata:
  openclaw:
    emoji: "🧩"
    requires: { anyBins: ["claude", "codex", "opencode", "pi"] }
---
# Coding Agent (bash-first)
Use bash for all coding agent work...
```

---

## 3. 工具策略系统

### 3.1 工具分组 (tool-policy.ts)

```typescript
// src/agents/tool-policy.ts

export const TOOL_GROUPS: Record<string, string[]> = {
  "group:memory": ["memory_search", "memory_get"],
  "group:web": ["web_search", "web_fetch"],
  "group:fs": ["read", "write", "edit", "apply_patch"],
  "group:runtime": ["exec", "process"],
  "group:sessions": ["sessions_list", "sessions_history", "sessions_send", ...],
  "group:ui": ["browser", "canvas"],
  "group:automation": ["cron", "gateway"],
  "group:messaging": ["message"],
  "group:nodes": ["nodes"],
  "group:openclaw": [/* 所有核心工具 */],
};
```

### 3.2 工具策略 Profile

```typescript
const TOOL_PROFILES: Record<ToolProfileId, ToolProfilePolicy> = {
  minimal: {
    allow: ["session_status"],  // 只允许状态查询
  },
  coding: {
    allow: ["group:fs", "group:runtime", "group:sessions", "group:memory", "image"],
  },
  messaging: {
    allow: ["group:messaging", "sessions_list", "sessions_history", ...],
  },
  full: {},  // 允许全部
};
```

### 3.3 工具名别名

```typescript
const TOOL_NAME_ALIASES: Record<string, string> = {
  bash: "exec",
  "apply-patch": "apply_patch",
};

export function normalizeToolName(name: string) {
  const normalized = name.trim().toLowerCase();
  return TOOL_NAME_ALIASES[normalized] ?? normalized;
}
```

---

## 4. Agent 执行引擎

### 4.1 核心执行流程 (pi-embedded-runner/run.ts)

```typescript
export async function runEmbeddedPiAgent(
  params: RunEmbeddedPiAgentParams,
): Promise<EmbeddedPiRunResult> {

  // 1. 解析模型
  const { model, error } = resolveModel(provider, modelId, agentDir, config);

  // 2. 上下文窗口检查
  const ctxGuard = evaluateContextWindowGuard({
    info: ctxInfo,
    warnBelowTokens: CONTEXT_WINDOW_WARN_BELOW_TOKENS,
    hardMinTokens: CONTEXT_WINDOW_HARD_MIN_TOKENS,
  });

  // 3. 认证配置解析
  const profileOrder = resolveAuthProfileOrder({ cfg, store, provider });

  // 4. 执行尝试 (带故障转移)
  while (profileIndex < profileCandidates.length) {
    try {
      return await runEmbeddedAttempt(params);
    } catch (error) {
      // 故障转移到下一个 profile
      profileIndex++;
    }
  }
}
```

### 4.2 模型故障转移

```typescript
// src/agents/failover-error.ts

export function resolveFailoverStatus(params: {
  classifyReason: (error) => FailoverReason;
  authProfiles: AuthProfile[];
  rateLimitProfiles: Set<string>;
}): FailoverResolveResult {
  // 检测认证失败、限流、上下文溢出、超时
  // 自动切换到下一个配置的模型
  // 跟踪 profile 冷却时间和失败次数
}

export type FailoverReason =
  | "auth"           // 认证失败
  | "rate_limit"     // 限流
  | "context"        // 上下文溢出
  | "timeout"        // 超时
  | "unknown";
```

### 4.3 系统提示构建 (system-prompt.ts)

```typescript
// 系统提示分段构建
function buildSystemPrompt(params) {
  return [
    buildSkillsSection(params),      // 技能说明
    buildMemorySection(params),      // 记忆搜索指引
    buildUserIdentitySection(params),// 用户身份
    buildTimeSection(params),        // 时间信息
    buildSafetySection(),            // 安全准则
    buildReplyTagsSection(params),   // 回复标签
    buildMessagingSection(params),   // 消息工具
    buildVoiceSection(params),       // 语音提示
    buildDocsSection(params),        // 文档路径
  ].flat().filter(Boolean).join('\n');
}
```

---

## 5. 多模型支持

### 5.1 隐式 Provider 发现

```typescript
// src/agents/models-config.providers.ts

export async function resolveImplicitProviders(context) {
  const providers = {};

  // 从环境变量自动发现
  if (process.env.ANTHROPIC_API_KEY) {
    providers["anthropic"] = { apiKey: process.env.ANTHROPIC_API_KEY, ... };
  }
  if (process.env.OPENAI_API_KEY) {
    providers["openai"] = { apiKey: process.env.OPENAI_API_KEY, ... };
  }
  // ... 更多 provider

  return providers;
}
```

### 5.2 Provider 合并策略

```typescript
// src/agents/models-config.ts

// 模式: "merge" (默认) 或 "replace"
// merge: 合并隐式发现 + 显式配置
// replace: 只使用显式配置

function mergeProviders({ implicit, explicit }) {
  const out = { ...implicit };
  for (const [key, config] of Object.entries(explicit)) {
    out[key] = implicit[key]
      ? mergeProviderModels(implicit[key], config)
      : config;
  }
  return out;
}
```

---

## 6. 配置系统

### 6.1 配置文件位置

- `~/.openclaw/openclaw.json` (用户配置)
- `<workspace>/.openclaw/config.json` (项目配置)

### 6.2 配置结构

```typescript
interface OpenClawConfig {
  agents?: {
    defaults?: {
      workspace?: string;
      model?: string;
      models?: string[];           // 模型列表用于故障转移
      sandbox?: SandboxConfig;
      thinking?: "off" | "low" | "medium" | "high";
    };
  };

  models?: {
    mode?: "merge" | "replace";
    providers?: Record<string, ProviderConfig>;
  };

  skills?: {
    allow?: string[];              // 允许的技能
    deny?: string[];               // 禁止的技能
    load?: {
      extraDirs?: string[];        // 额外技能目录
    };
  };

  tools?: {
    exec?: { timeout?: number };
    fileOps?: { maxFileSize?: number };
  };
}
```

---

## 7. 对我们项目的借鉴价值

### 7.1 Skill 系统设计

| OpenClaw | 我们可借鉴 |
|----------|-----------|
| YAML frontmatter + Markdown | 结构化配置 + 可读文档 |
| `requires.bins/env/os` | 运行前检查依赖可用性 |
| `install` 规格 | 自动安装缺失依赖 |
| 三层加载优先级 | bundled < managed < workspace |
| `shouldIncludeSkill` | 资格检查函数 |

**建议改进我们的格式**：

```yaml
---
name: stock
description: 股票分析专家
provider: deepseek
requires:
  env: ["ALPHA_VANTAGE_KEY"]
  bins: []
install:
  - kind: pip
    package: yfinance
---

## System Prompt
你是一个专业的股票分析师...

## Skills
### 行情查询
查询股票实时价格

## Tools
- stock_quote
- stock_news
```

### 7.2 工具策略系统

```python
# 建议实现
TOOL_GROUPS = {
    "group:fs": ["read", "write", "edit"],
    "group:web": ["web_search", "web_fetch"],
    "group:stock": ["stock_quote", "stock_news"],
}

TOOL_PROFILES = {
    "minimal": {"allow": ["get_current_time"]},
    "coding": {"allow": ["group:fs", "exec"]},
    "stock": {"allow": ["group:stock", "group:web"]},
    "full": {},  # 允许全部
}
```

### 7.3 模型故障转移

```python
# 建议实现
FAILOVER_CHAIN = ["deepseek", "grok", "openai", "claude"]
PROFILE_COOLDOWN = 60  # 失败后冷却秒数

async def chat_with_failover(message, providers):
    for provider in providers:
        if is_in_cooldown(provider):
            continue
        try:
            return await llm.chat(message, provider=provider)
        except (AuthError, RateLimitError):
            mark_failed(provider)
    raise AllProvidersFailedError()
```

### 7.4 Workspace 上下文注入

OpenClaw 在首轮对话注入这些文件：
- `AGENTS.md` — Agent 指令和记忆
- `SOUL.md` — 人格边界
- `USER.md` — 用户画像
- `MEMORY.md` — 长期记忆

**建议我们实现**：

```
~/.ai-assistant/
├── AGENTS.md      # Agent 全局指令
├── USER.md        # 用户偏好画像
└── MEMORY.md      # 长期记忆
```

---

## 8. 代码复杂度观察

| 模块 | 文件数 | 复杂度 |
|------|--------|--------|
| src/agents/ | 297 | 极高 |
| src/config/ | 122 | 高 |
| src/channels/ | 33 | 中 |
| skills/ | 52 | 低 (主要是文档) |

OpenClaw 的 Agent 系统非常复杂，包含大量边缘情况处理：
- 多账户认证和故障转移
- 上下文窗口管理和压缩
- 工具策略和权限控制
- 会话管理和子 Agent 协作

**对我们的启示**：先实现核心功能，逐步添加复杂性。

---

## 9. 总结

### 核心设计理念

1. **Skill 是知识库** — Markdown 文档描述能力和使用方法
2. **requires 是门卫** — 运行前检查依赖可用性
3. **三层优先级** — 允许项目级覆盖全局配置
4. **工具策略** — 细粒度控制 Agent 能力
5. **模型故障转移** — 自动处理 API 失败

### 建议我们优先实现

1. **Skill 格式增强** — 添加 requires 字段
2. **三层加载机制** — bundled < managed < workspace
3. **工具分组策略** — group:fs, group:web 等
4. **模型故障转移** — 自动切换模型
5. **Workspace 上下文** — 注入 AGENTS.md, USER.md
