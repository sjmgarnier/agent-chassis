# Chassis

A composable agent configuration system. Instead of a monolithic `CLAUDE.md` that accumulates every instruction you've ever needed, chassis splits your configuration into modular components that are injected on demand based on the incoming prompt.

---

## The idea

Your agent instructions fall into two categories:

- **Universal rules** — things that always apply, regardless of what you're doing. These belong in `CLAUDE.md`.
- **Domain-specific instructions** — your git workflow, your R packaging conventions, this API's authentication quirks. These change by context, and loading all of them all the time pollutes the context window with instructions that don't apply.

Chassis manages the second category. Components are markdown files with YAML frontmatter declaring their trigger conditions. A hook script fires before each prompt, matches the prompt against component triggers, and injects matching components into context — before the agent sees the message.

```
~/.chassis/components/
  COMPONENT-git.md        # injected when prompt mentions git, commit, branch...
  COMPONENT-r-pkg.md      # injected when prompt mentions devtools, roxygen...
  COMPONENT-api-auth.md   # injected when prompt mentions auth, token, OAuth...

<project>/.components/
  COMPONENT-git.md        # project-level override of the global git component
```

---

## How it differs from skills

[Superpowers skills](https://github.com/anthropics/claude-code) and chassis solve related but distinct problems. The confusion is understandable — both inject instructions into context. Here is where they diverge.

### Push vs pull

Skills are **agent-pull**: the agent reads your prompt, decides a skill applies, and invokes it. That works well for workflow methodology skills (TDD, brainstorming, debugging) where the agent reliably recognises the need.

Chassis is **hook-push**: a script fires before the agent sees the prompt, matches components, and injects them. The agent cannot forget to load context it never had to ask for.

This distinction matters most when:
- The agent is mid-task and hasn't paused to reconsider its tooling
- Context compaction has wiped out previously loaded instructions
- The relevant domain isn't obvious from the prompt surface (e.g. a vague "fix this" over code that requires specific project conventions)

### Workflow methodology vs domain knowledge

Skills are about **how to do things** — the TDD cycle, how to brainstorm a design, how to debug systematically. They are universal techniques that apply the same way regardless of project.

Chassis components are about **the rules for this specific context** — how commits are formatted in this repo, what testing framework this project uses, which authentication pattern this API expects. They are authored by the user, scoped to their environment, and mean nothing outside it.

### Compaction resilience

After context compaction, any skill the agent loaded earlier in the session is gone. The agent would need to notice this and re-invoke the skill — which it often doesn't. Chassis re-injects components automatically on every prompt, so compaction is a non-event.

---

## How it complements skills

Chassis and skills are not competitors. They occupy different layers:

| Layer | Mechanism | What it carries |
|---|---|---|
| `CLAUDE.md` | Always loaded | Universal, stable rules |
| Skills | Agent-pull | Workflow methodology |
| Chassis | Hook-push | Domain-specific instructions |

A session might load the brainstorming skill when you ask it to design a feature, and simultaneously have the git-workflow and r-packaging components injected because your prompt mentioned commits and a package test. They coexist without interference.

The practical split: if you're writing an instruction that tells the agent *how to approach a class of problem*, it's a skill. If you're writing an instruction that encodes *the conventions of your specific environment*, it's a chassis component.

---

## Overlaps

It is possible to do either job with the wrong tool:

- A skill can encode project-specific conventions. It works, but the agent has to remember to invoke it, and after compaction it's gone.
- A chassis component can encode workflow methodology. It works, but it gets injected whether the prompt needs it or not.

The tools overlap in capability. They differ in reliability and appropriate scope.

---

## Cheeky take

If skills are the right abstraction for workflow methodology, chassis is what you reach for when skills aren't reliable enough: project-specific instructions that must be present, must survive compaction, and must not depend on the agent remembering to ask for them.

Or, put differently: chassis is skills with a push model, scoped to your environment instead of a universal technique library.

---

## Use cases

> *Specific examples comparing chassis and skills for the same task will be added here as the project matures.*

Early candidates:
- Project-specific git commit conventions (chassis) vs general commit hygiene guidance (skill)
- This codebase's testing patterns (chassis) vs TDD methodology (skill)
- A private API's authentication flow (chassis) vs general API integration patterns (skill)
- Post-compaction context restoration (chassis has no equivalent in skills)

---

## Status

Under active development. See [`docs/superpowers/specs/2026-05-26-chassis-design.md`](docs/superpowers/specs/2026-05-26-chassis-design.md) for the full design spec and [`docs/superpowers/plans/`](docs/superpowers/plans/) for the implementation plan.
