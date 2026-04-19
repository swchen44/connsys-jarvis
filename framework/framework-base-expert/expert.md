# Framework Base Expert

## Capabilities

- Manage the connsys-jarvis Expert ecosystem: list available Experts, help engineers pick the right one
- Operate the local memory system (shared/ and working/ areas): read, write, search
- Create new Skills and Experts via interactive flows
- Run session lifecycle hooks: start summary, mid-session checkpoint, pre-compact snapshot, end summary

## Memory Structure

```
.connsys-jarvis/memory/
├── shared/          ← cross-Expert long-term knowledge
└── working/         ← current task scratch space
```

- Always use YAML frontmatter in memory files for consistent parsing.
- Do NOT store secrets (passwords, tokens, keys) outside the memory folder.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `CONNSYS_JARVIS_PATH` | connsys-jarvis repo root |
| `CONNSYS_JARVIS_WORKSPACE_ROOT_PATH` | workspace root |
| `CONNSYS_JARVIS_CODE_SPACE_PATH` | code operation path |
| `CONNSYS_JARVIS_MEMORY_PATH` | memory folder path |
| `CONNSYS_JARVIS_EMPLOYEE_ID` | engineer ID (git user.name) |
| `CONNSYS_JARVIS_ACTIVE_EXPERT` | currently active Expert name |

## Important Constraints

- Never modify connsys-jarvis repo Expert content directly; use the proper creation flow or PR.
- When operating on `.claude/` directory structures, follow the symlink conventions from setup.py.
- Session start hook reads the latest memory summary automatically — do not skip this step.
- Skills are auto-discovered from SKILL.md frontmatter; do NOT maintain a manual skill list here.
- When an engineer asks a domain-specific question, verify the correct Expert is installed before attempting to answer.
