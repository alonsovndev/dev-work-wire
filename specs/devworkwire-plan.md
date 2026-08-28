# DevWorkWire — Product Plan & Overview

**Project name:** DevWorkWire
**CLI command:** `dwire`
**Organization:** [github.com/alonsovndev](https://github.com/alonsovndev)

---

## 1. What DevWorkWire Does

DevWorkWire is an **open-source** tool that takes an **already-defined, refined** structure of work (Epics with their User Stories and Acceptance Criteria) and loads it, validated and reliably, into a project-tracking system (Jira first) — usable directly by a developer through an **interactive CLI** (`dwire`), or by an **AI agent** through DevWorkWire's own **MCP server**.

**Important — scope clarification:** DevWorkWire does not receive free-form or unstructured text that needs to be interpreted or "refined" by the tool. The input already arrives defined and ready to import (for example, a Markdown document with the Epic → Story → Acceptance Criteria hierarchy already complete). DevWorkWire's job is not to guess intent from ambiguous prose, but to **validate that the already-defined structure is correct and consistent** before writing it to Jira, show a clear preview, and avoid duplicates on re-run.

Core loop:
1. The user (or an upstream AI agent) provides an already-defined structure — Epics → Stories → Acceptance Criteria.
2. DevWorkWire **validates and previews** it (counts, consistency checks — e.g., correct parent/child links) before writing anything.
3. On confirmation, it **creates/updates** items in the tracking system.
4. As work progresses, DevWorkWire retrieves context for an item (description, AC, comments) and **reports progress back** (comments, status transitions) — driven by a human via CLI, or by an LLM agent via MCP.

**Positioning:** *"Load an already-defined work structure into your backlog, validated and duplicate-free — by hand or with your AI agent driving."*

---

## 2. Scope

**In scope (all phases):**
- Structured loading of already-defined Epics/Stories/AC, with mandatory validation and preview before writing
- Reading work-item context (description, AC, comments, status, sprint)
- Writing back progress: comments, status transitions, linking progress (e.g., a PR URL) to a work item
- One interactive CLI (`dwire`) and one MCP server, both built on the same core service — no divergent logic between "human mode" and "agent mode"

**Out of scope (all phases):**
- Interpreting or "refining" free-form/ambiguous text into structure — that responsibility belongs to whoever prepares the input (a person or an upstream agent), not DevWorkWire
- Git or GitHub automation (branching, committing, PR creation) — left to the developer's existing coding-agent skills/tooling
- Acting as a replacement for the project-management UI — DevWorkWire is a bridge, not a Jira/Linear replacement

---

## 3. Provider Scope: Jira First, Extensible Later

- **Phase 1: Jira only.** Full depth here before broadening — custom field mapping, real transition-name discovery, correct epic/story hierarchy handling.
- **Later phases: Linear, Azure DevOps**, added as new adapters behind the same `WorkItemProvider` port — no changes to the core service, CLI, or MCP tool definitions required. This is the reason for the hexagonal architecture from day one, even though only one adapter ships initially.
- A project using DevWorkWire declares its provider in `devworkwire.yml`; the core doesn't need to know which one it's talking to.

---

## 4. LLM Harness Scope: Any MCP-Compatible Agent, Not Just Claude

DevWorkWire's MCP server is built to the open MCP protocol, so it works with **any MCP-compatible harness** — Claude (Code, Desktop, Cowork), OpenCode, GitHub Copilot, Antigravity, and future entrants — with no per-harness custom integration. Claude is the primary target for early testing given the project author's existing tooling, but nothing in the design is Claude-specific.

This is a natural consequence of building DevWorkWire's *own* MCP server directly against the Jira REST API (decided previously) rather than depending on any single vendor's agent SDK.

---

## 5. Two Front Doors, One Core

```
                 Application / Domain
                 (WorkItemService)
                         │
                ┌────────┴────────┐
                │                 │
         Interactive CLI      DevWorkWire MCP Server
          (dwire, human-       (any MCP-compatible agent:
           driven)              Claude, OpenCode, Copilot,
                                 Antigravity, ...)
                │                 │
                └────────┬────────┘
                         │
                  Provider Port
                (WorkItemProvider)
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
            Jira       Linear     Azure DevOps
           Adapter    Adapter      Adapter
          (Phase 1)   (later)      (later)
```

---

## 6. Features

**Loading engine (headline feature)**
- Receives an already-defined structure (Epic → Story → AC) in an agreed format (e.g., already-structured Markdown)
- Validates consistency: counts, correct parent/child links, required fields present
- Preview before writing anything
- Mandatory confirmation before executing (`import.commit`)
- Re-running the same file as an update pass without creating duplicates (matched by provider key or a stored import-source reference)
- Preview persists briefly (short-lived local file, not memory-only) so a preview generated in one interface (CLI) can be confirmed from another (an agent session) within the same window

**Work-item context retrieval**
- Show full detail: description, AC, comments, status, sprint, linked issues
- Search: structured filters + native query language (JQL for Jira) via CLI; equivalent MCP tool for agents
- List by common filters (assigned to me, in current sprint, by status)

**Progress write-back**
- Add comment (with idempotency hint to avoid duplicate comments from agent retries)
- Transition status (checked against the provider's actual configured transition names, auto-discovered and cached, with manual override available in config for edge cases)
- Composed "report progress" action: comment + transition together, for the common "PR opened → mark in review" moment

**Interactive CLI (`dwire`)**
- List-picker style search & select (fzf-style)
- Insert/attach by existing item ID
- Guided bulk-loading flow (validate → preview → confirm)
- Item detail view with inline comment/transition actions

**MCP server**
- Same tool set as the CLI's underlying service, exposed for any MCP-compatible agent
- Autonomous bulk loading allowed, but gated behind the same `import.preview` → `import.commit` confirm step as the CLI — no separate, looser code path for agents

---

## 7. Trust Tiers

| Tier | Examples | Default behavior |
|---|---|---|
| Read-only | show / search / list | Fully autonomous |
| Externally visible | comment, transition, import commit | Confirm-before-execute by default; relaxable per-project once trusted |

---

## 8. Phased Roadmap

**Phase 1 — MVP (Jira, Claude-tested, any-MCP-agent-capable)**
- Core service (`WorkItemService`) with Jira adapter
- Loading engine: validation + preview + confirmation, with dedup on re-run
- Interactive CLI (`dwire`): search/select, insert-by-id, guided load
- DevWorkWire's own MCP server exposing the same tool set
- Trust-tier confirm gate on all externally-visible actions
- Config (`devworkwire.yml`): project keys, field mappings, provider selection
- Proper packaging (`pyproject.toml`) and publish to PyPI as `devworkwire`, with the `dwire` command entry point; document `pipx install devworkwire` as the recommended install path

**Phase 2 — Hardening & smarter automation**
- Pluggable "what's next" ranking (beyond raw priority/sprint order — respecting story dependencies)
- Auto-discovery + caching of provider-specific transition names, with config override
- Broader idempotency coverage and edge-case handling from real usage
- Community feedback loop now that MVP is usable end-to-end
- Homebrew tap (`brew tap alonsovndev/devworkwire && brew install devworkwire`); evaluate Homebrew core and standalone binaries once there's real traction

**Phase 3 — Multi-provider**
- Linear adapter
- Azure DevOps adapter
- No changes needed to CLI, MCP tool definitions, or core service — validates the adapter boundary was drawn correctly in Phase 1

**Phase 4 — Governance (only if real demand emerges)**
- Optional audit trail of agent-driven writes
- Optional policy layer (who/what can bypass the confirm gate) for teams that want it
- Not part of the open-source core roadmap unless clearly needed — avoid building this speculatively

---

## 9. Distribution & Installation

- **PyPI** (`pip install devworkwire`) — the baseline distribution channel; installs the `dwire` command.
- **pipx** (`pipx install devworkwire`) — the recommended install path for Python CLIs today, isolating the tool without polluting the global environment. Documented as the primary recommendation in the README.
- **Homebrew tap** (`brew tap alonsovndev/devworkwire && brew install devworkwire`) — a self-maintained tap under the `alonsovndev` organization, not dependent on Homebrew core's approval process.
- **Homebrew core** (plain `brew install devworkwire`) — deferred until the project has real traction and meets Homebrew's notability/maintenance criteria; not a Phase 1 goal.
- **Standalone binaries** via GitHub Releases (e.g., PyInstaller/Shiv) — useful for users who don't want a Python environment at all, particularly on Windows. Deferred until there's demand.

Packaging must be done properly (`pyproject.toml`, versioning, changelog) from Phase 1, since it's the foundation every later distribution channel builds on.

---

## 10. Open Source Model

- Fully open source, **MIT license** — maximizes adoption and lowers friction for community-contributed provider adapters (Linear, Azure DevOps) and harness-specific testing.
- Published under the [alonsovndev](https://github.com/alonsovndev) GitHub organization.
- No paid tier planned. Governance/audit features (Phase 4) stay part of the open core unless a clear, real need for a separate offering emerges later — not a decision to make speculatively now.

---

## 11. Naming History (for context)

Considered and discarded: WorkFoundry (original name — repositioned away from git/GitHub automation), Devflow (conflicts with an existing AI-powered dev workflow automation tool of the same name), Flowgate (conflicts with `flowgate-cli`, same domain), Workwire (package name free, but domain and brand heavily used by HR/staffing companies), Devwire (conflicts with three active organizations, including a DevOps consultancy), Codewire (conflicts with an existing dev-tools project). **DevWorkWire** was chosen as a three-word combination with no found conflicts in PyPI, GitHub, or existing branding, with `dwire` as a short, available CLI alias.

---

## 12. Remaining Open Question

- Exact shape of the pluggable "what's next" ranking in Phase 2 — likely worth revisiting once there's real backlog data to test against, rather than designing it abstractly now.