---
name: framework-expert-create-flow
description: "Interactively create a new connsys-jarvis Expert — covering expert.json, soul.md, rules.md, duties.md, expert.md, and folder scaffolding. Use whenever a developer wants to build a new Expert from scratch, add a new domain, or create a base expert. Triggers on: 'create expert', 'new expert', 'add expert', 'build expert', 'make expert', or when someone describes a new domain capability that needs its own Expert."
version: "1.0.0"
domain: framework
type: flow
scope: framework-base-expert
tags: [framework, expert-creator, flow, development]
---

# Framework Expert Create Flow

An interactive wizard for creating a complete, standards-compliant connsys-jarvis Expert. This skill walks through every required file and folder, validates naming, and ends with a checklist against the requirements doc.

Reference: [gitagent SPECIFICATION](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md) — connsys-jarvis follows the same SOUL / RULES / DUTIES pattern.

---

## Step 0: Prerequisite Check

Before writing any files, collect the following. Ask if not provided — don't guess.

1. **Domain** — which domain does this expert belong to? (e.g., `wifi-bora`, `sys-bora`, `framework`)
2. **Expert name** — what is the purpose? (full name will be `{domain}-{purpose}-expert`)
3. **Is it a base expert?** — shared resource container (`is_base: true`) or a specific-task expert?
4. **Owner team** — which team maintains it? (e.g., `wifi-bora-team`)
5. **Dependencies** — which existing experts does it depend on? (e.g., `framework-base-expert`, `wifi-bora-base-expert`)
6. **Core purpose** — one sentence: what does this expert enable Claude to do?

Propose the full expert name and confirm with the user before creating any files.

---

## connsys-jarvis Expert Naming Rules

**Format**: `{domain}-{purpose}-expert`

| Part | Rules | Examples |
|------|-------|---------|
| `domain` | Layer 1 domain prefix | `wifi-bora`, `sys-bora`, `bt-bora`, `framework` |
| `purpose` | kebab-case description | `memory-slim`, `preflight`, `cr-robot`, `base` |
| suffix | always `-expert` | — |

**Special case — Base Expert**:
- Every domain must have exactly one `{domain}-base-expert`
- Set `is_base: true` in expert.json
- No dependencies (other experts depend on it, not the other way)
- Acts as a shared skill/hook/command container for its domain

**Expert directory path**: `connsys-jarvis/{domain}/{domain}-{purpose}-expert/`

---

## Step 1: Create the Directory Structure

Scaffold the full Layer 4 structure:

```
{domain}/{domain}-{purpose}-expert/
├── expert.json     ← Manifest (required)
├── soul.md         ← Identity & personality (required)
├── rules.md        ← Hard constraints (required)
├── duties.md       ← Role boundaries (required)
├── expert.md       ← Key behaviors & tools (required, loaded into CLAUDE.md)
├── README.md       ← Traditional Chinese documentation (required)
├── skills/         ← Skill folders (use framework-skill-create-flow to create each)
├── hooks/          ← Lifecycle shell scripts (optional)
├── agents/         ← Sub-agent definitions (optional)
└── commands/       ← Slash command definitions (optional)
```

Create the directory, then proceed file by file.

---

## Step 2: Write expert.json

### Schema

```json
{
  "name": "{domain}-{purpose}-expert",
  "display_name": "{Human Readable Name}",
  "domain": "{domain}",
  "owner": "{domain}-team",
  "description": "{one-sentence description}",
  "version": "1.0.0",

  // Base expert only — omit for regular experts:
  "is_base": true,

  // Triggers: keywords that suggest this expert should be active
  "triggers": ["keyword1", "keyword2"],

  // State-machine transitions: when condition X is met, suggest switching to expert Y
  "transitions": {
    "ANALYSIS_DONE": "{domain}-{next}-expert"
  },

  // Dependencies: which experts' assets to symlink into .claude/
  "dependencies": [
    {
      "expert": "framework/framework-base-expert",
      "skills": ["framework-expert-discovery-knowhow", "framework-memory-tool"],
      "hooks": ["all"],
      "agents": [],
      "commands": ["framework-experts-tool"]
    }
    // Add domain base-expert dependency if applicable
  ],

  // Internal: this expert's own skills/hooks/agents/commands
  "internal": {
    "skills": [],
    "hooks": [],
    "agents": [],
    "commands": []
  },

  // Scenarios this expert supports
  "scenarios": ["agent-first", "legacy"],

  // Operations requiring human confirmation before execution
  "human_in_the_loop": {
    "require_confirm": ["git push", "git reset --hard", "rm -rf"]
  },

  // Regex patterns for symlinks to exclude after creation
  "exclude_symlink": {
    "patterns": []
  }
}
```

### Dependencies selection rules

| Situation | Write | Effect |
|-----------|-------|--------|
| Inherit all | `"skills": ["all"]` | Symlink every skill from that expert |
| Explicit list | `"skills": ["foo-tool", "bar-flow"]` | Only symlink named skills |
| Omit key | (don't write `"skills"`) | Inherit nothing |

> `hooks`, `agents`, `commands` follow the same rule independently.

---

## Step 3: Write soul.md

soul.md defines **who this expert is**. Write in the voice of the expert itself.

**Required sections**:

```markdown
# {ExpertName} — Soul

## Identity

{One clear sentence: who is this expert and what is its singular purpose?}

## Communication Style

{How does it communicate? Examples:}
- Direct and technical — uses precise terminology, no fluff
- Collaborative — explains reasoning, invites confirmation before acting
- Language: Traditional Chinese (technical terms remain in English)

## Values & Principles

{3–5 core values. Each should reflect what the expert genuinely prioritizes.}
- **{Value}**: {Why this matters for this expert's domain}

## Domain Expertise

{What does this expert know deeply?}
- {Specific domain knowledge 1}
- {Specific domain knowledge 2}

## Personality

{1–2 sentences describing disposition and working style.
Example: "Proactive but aware of its own boundaries. Asks rather than guesses when uncertain."}

## Collaboration Style

{How does it work with the engineer?}
- When to ask vs. act autonomously
- Tone and escalation behavior
```

**Tips**:
- Identity = one sentence, no ambiguity
- Values should differ from other experts — what is *unique* about this expert's priorities?
- Domain expertise is factual, not generic ("Wi-Fi 802.11 protocol stack" not "software development")

---

## Step 4: Write rules.md

rules.md defines **hard constraints** — behaviors that never change regardless of context.

**Required sections**:

```markdown
# {ExpertName} — Rules

## Must Always

- {Non-negotiable behavior 1 — what must this expert do in all circumstances?}
- {Non-negotiable behavior 2}
- Example: "Confirm with the engineer before high-risk operations (git push, file deletion)"
- Example: "Read the latest memory summary at session start"

## Must Never

- {Hard boundary 1 — what is absolutely forbidden?}
- {Hard boundary 2}
- Example: "Execute irreversible operations without explicit confirmation"
- Example: "Store sensitive information (passwords, tokens, private keys) outside the memory folder"

## Output Constraints

- {Format rules for outputs this expert produces}
- Example: "All memory documents use YAML frontmatter + Markdown"
- Example: "All memory keys use snake_case"

## Interaction Boundaries

- {Scope limits — what does this expert NOT do?}
- Example: "Do not execute concrete technical tasks belonging to other domains"
- Example: "Do not make architectural decisions on behalf of the engineer — provide options and analysis only"

## Conflict Resolution

- {If two rules conflict, which takes priority?}
- Example: "When rules conflict, protecting the engineer's work from loss takes highest priority"
```

**Tips**:
- Must Always / Must Never should be short, concrete, and unambiguous
- Avoid vague rules like "be helpful" — these aren't constraints
- Output Constraints should match what this expert actually produces
- Interaction Boundaries is where you define the segregation of duties

---

## Step 5: Write duties.md

duties.md defines **role responsibilities and what this expert explicitly does NOT do**.

**Required sections**:

```markdown
# {ExpertName} — Duties

## Primary Duties

### 1. {Main responsibility name}
- {Specific task 1}
- {Specific task 2}

### 2. {Second responsibility}
- {Specific task 1}

## Segregation of Duties

- **Does not execute** {what belongs to other experts, not this one}
- **Does not directly operate** {tools or systems owned by other experts}
- **Does not make** {decision types that belong elsewhere}

## KPIs (optional)

{Measurable success indicators, if meaningful}
- {KPI 1}: {target}
- {KPI 2}: {target}
```

**Tips**:
- Primary Duties = what this expert *does*; be specific, not generic
- Segregation of Duties is critical for multi-expert systems — prevents overlap and confusion
- KPIs are optional but useful for measurable domains (latency, accuracy, etc.)

---

## Step 6: Write expert.md

expert.md is the **public interface** of this expert — setup.py @includes this into CLAUDE.md. Claude reads this every session. Keep it factual and current.

**Required sections**:

```markdown
# {Expert Display Name}

## Overview

{2–3 sentences: what this expert does, when to use it, what domain it covers}

## Key Behaviors

- {Observable behavior 1}
- {Observable behavior 2}
- Example: "Automatically reads the latest memory summary at session start"

## Tools Available

| Command | Description |
|---------|-------------|
| `/{command}` | {what it does} |

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `{domain}-{name}-{type}` | {type} | {one-line description} |

## Hooks

| Hook | Trigger | Description |
|------|---------|-------------|
| `{hook}.sh` | {when} | {what it does} |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CONNSYS_JARVIS_*` | {description} |

## Memory Structure (if applicable)

{Describe what this expert reads/writes to .connsys-jarvis/memory/}
```

**Tips**:
- This file is loaded every session — keep it concise and accurate
- Skills and Hooks tables should stay in sync with expert.json internal list
- Do not duplicate soul.md content here — expert.md is behavioral, not identity

---

## Step 7: Set Up Content Folders

### skills/
Each skill follows `{domain}-{name}-{type}/` naming. Use `framework-skill-create-flow` to create each skill interactively — it handles SKILL.md, README.md, expert.json registration, naming validation, and eval setup.

```
skills/
└── {domain}-{name}-{type}/
    ├── SKILL.md
    └── README.md
```

Typical skill types for a new expert:
- `flow`: the primary SOP or workflow this expert executes
- `knowhow`: domain knowledge reference (architecture, protocol, code rules)
- `tool`: external tool operation guides

### hooks/
Shell scripts that run at lifecycle events. Shell-first; complex logic in `{name}-helper.py`.

```
hooks/
├── session-start.sh      ← Load memory
├── session-end.sh        ← Save session summary
├── pre-compact.sh        ← Snapshot before context compression
└── mid-session-checkpoint.sh  ← Periodic save (every ~20 messages)
```

Only add hooks this expert genuinely needs. Base experts typically have all four.

### agents/
Sub-agent prompt files. Each `.md` file defines a specialized subagent Claude can spawn.

```
agents/
└── {agent-name}.md    ← System prompt / instructions for the subagent
```

Use sub-agents for: parallel tasks, specialized analysis (log parsing, doc lookup), or operations that benefit from fresh context.

### commands/
Slash command definitions. Type is always `tool`.

```
commands/
└── {domain}-{name}-tool/
    └── COMMAND.md
```

Phase 1: inherit commands from framework-base-expert; only add new commands when the expert needs unique slash commands not available in its dependencies.

---

## Step 8: Write README.md

Write in **Traditional Chinese (Taiwan)**. Follow the template from `framework-skill-create-flow`'s README.md (sections: Introduction, Owner, Features, Goals, Design Philosophy, Risks, Alternatives, Source).

---

## Step 9: Register and Install

After all files are written:

1. **Check the directory path** is correct: `connsys-jarvis/{domain}/{expert-name}/`

2. **Install with setup.py** to verify the expert works end-to-end:
   ```bash
   # First-time install (replaces current expert):
   uv run ./connsys-jarvis/scripts/setup.py --init {domain}/{expert-name}/expert.json && source .connsys-jarvis/.env

   # Add alongside existing expert:
   uv run ./connsys-jarvis/scripts/setup.py --add {domain}/{expert-name}/expert.json && source .connsys-jarvis/.env
   ```

3. **Run doctor** to validate:
   ```bash
   uv run ./connsys-jarvis/scripts/setup.py --doctor
   ```

---

## Step 10: Create Expert Checklist

Run through every item before considering the expert complete.

### A. Directory & Files

- [ ] Expert directory at correct path: `connsys-jarvis/{domain}/{domain}-{purpose}-expert/`
- [ ] `expert.json` — valid JSON, all required fields present
- [ ] `soul.md` — has Identity, Communication Style, Values, Domain Expertise, Personality, Collaboration Style
- [ ] `rules.md` — has Must Always, Must Never, Output Constraints, Interaction Boundaries, Conflict Resolution
- [ ] `duties.md` — has Primary Duties, Segregation of Duties
- [ ] `expert.md` — has Overview, Key Behaviors, Skills table, Hooks table
- [ ] `README.md` — in Traditional Chinese, has all required sections

### B. expert.json Validation

- [ ] `name` matches directory name exactly
- [ ] `domain` matches the domain prefix
- [ ] `version` is `"1.0.0"` for new experts
- [ ] `dependencies` lists `framework/framework-base-expert` (unless this IS framework-base-expert)
- [ ] `internal.skills` lists all skills in the `skills/` folder
- [ ] `internal.hooks` lists all hooks in the `hooks/` folder
- [ ] `is_base: true` if this is a base expert; field absent for regular experts
- [ ] `human_in_the_loop.require_confirm` covers all destructive operations in this domain

### C. Content Quality

- [ ] soul.md Identity is one clear sentence (not vague)
- [ ] rules.md Must Never items are concrete and unambiguous
- [ ] duties.md Segregation of Duties explicitly names what other experts own
- [ ] expert.md Skills table matches `expert.json internal.skills`
- [ ] expert.md Hooks table matches `expert.json internal.hooks`

### D. Skills

- [ ] Each skill created using `framework-skill-create-flow`
- [ ] Each skill name follows `{domain}-{name}-{type}` format
- [ ] Each skill registered in `expert.json internal.skills`

### E. Installation Validation

- [ ] `setup.py --doctor` passes all checks

### F. Requirements Alignment

- [ ] Expert follows naming rule from requirements §1.3 / design §2.4
- [ ] Base expert has `is_base: true` (FR-05-7/FR-05-8)
- [ ] `human_in_the_loop` covers all operations flagged as risky in requirements
- [ ] `transitions` defined if this expert has a natural successor in the workflow

---

## Reference

- `connsys-jarvis/doc/agents-design.md` — §2.4 (Expert naming), §2.5 (Layer 4 structure), §4 (expert.json format)
- `connsys-jarvis/doc/agents-requirements.md` — FR-01, FR-03, FR-05 (Expert rules)
- [gitagent SPECIFICATION](https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md) — SOUL/RULES/DUTIES pattern reference
- `framework-skill-create-flow` — use this to create each skill inside the new expert
