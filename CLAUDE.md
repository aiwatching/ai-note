# eng — 英语输出练习

这个仓库只有一个用途：训练 `意思 → 英文` 的检索路径。不是词汇、不是听力、不是语法。

**用户想练英语时（说 /eng、"练英语"、"来一题"、"练口语输出"），
先读 `.claude/skills/eng/SKILL.md` 并完全按它执行。** 那里面的硬规则不是风格偏好，
是这个训练唯一有效的原因 —— 尤其是"他开口之前不给任何英文"和"重复判定只信 drill.py"。

数据在 `engdata/entries.jsonl`（跟着 git 走，云端 clone 下来就能用）。
API key 在 `~/.eng/config`，**故意不在仓库里**；云端会话没有它，
`drill.py` 也强制 `ENG_LLM=off` —— 陪练时你自己就是那个 LLM。

<!-- forge:template:obsidian-vault -->
## Obsidian Vault
Location: /Users/zliu/MyDocuments/obsidian-project/Projects
When I ask about my notes, use bash to search and read files from the vault directory.
Example: find <vault_path> -name "*.md" | head -20
<!-- /forge:template:obsidian-vault -->
