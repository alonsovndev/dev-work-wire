# AI agent skill

DevWorkWire ships a portable [Agent Skills](../../skills/devworkwire/SKILL.md)
instruction file for AI tools that can run local shell commands. The skill
teaches the agent to use the installed `dwire` CLI; it is not a separate Jira
client and does not grant permissions.

## Set up

1. Install and configure `dwire` as described in [Installation](../getting-started/installation.md)
   and [Configuration](../getting-started/configuration.md).
2. Verify `dwire --help` and a read-only command such as
   `dwire --format json preview-folder path/to/work-items` in the shell the
   agent will use.
3. Copy the `skills/devworkwire/` folder to the skill directory recognized by
   your AI tool. For Codex, use `.codex/skills/devworkwire/` in a project or
   `~/.codex/skills/devworkwire/` for your user account. For Claude Code, use
   `.claude/skills/devworkwire/` in a project. Other clients should use their
   documented Agent Skills location.

The `SKILL.md` file is self-contained, so copying its folder does not require
the DevWorkWire source checkout. It assumes the agent's shell can find `dwire`
and access the same configuration and work-item folder as the user.

## Approval and write behavior

An agent may run a write command only within the user's approved task. The CLI
cannot inspect that approval. `create-epic` and `create-story` write immediately;
`import-folder --yes` performs its local preview and then writes without a
terminal prompt. Review the agent's task and the local folder preview before
authorizing an import. A changed source item already recorded as uploaded is
skipped; the current CLI does not update it in Jira.

If an import reports `partial`, inspect the created keys and Jira before
retrying. Use `resolve-import` only after checking whether Jira created the
uncertain item. See the [CLI Reference](cli-reference.md) for the full command
and result contract.
