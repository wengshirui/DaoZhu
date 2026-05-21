"""AccoBot Skill system — procedural knowledge as markdown files.

Skills are reusable operation procedures stored as SKILL.md files.
They tell the agent HOW to perform specific tasks (e.g., "how to file VAT
on Guangdong e-tax website").

Architecture (inspired by Hermes Agent):
- Skills stored in ~/.accobot/skills/{name}/SKILL.md (user, read-write)
- Built-in skills in accobot/skills/ (bundled, read-only)
- Two-tier disclosure: compact index in system prompt, full content on demand
- Skill content injected as user message (preserves prompt cache)
"""
