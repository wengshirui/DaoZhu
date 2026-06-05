---
name: design-an-interface
description: Generate multiple radically different interface designs for a module using parallel sub-agents. Use when user wants to design an API, explore interface options, compare module shapes, or mentions "design it twice".
version: 1.0.0
author: mattpocock
---

# Design an Interface

Based on Design It Twice from A Philosophy of Software Design - your first idea is unlikely to be the best. Generate multiple radically different designs, then compare.

## Workflow

### 1. Gather Requirements

Before designing, understand:

- What problem does this module solve?
- Who are the callers? (other modules, external users, tests)
- What are the key operations?
- Any constraints? (performance, compatibility, existing patterns)
- What should be hidden inside vs exposed?

Ask: What does this module need to do? Who will use it?

### 2. Generate Designs (Parallel Sub-Agents)

Spawn 3+ sub-agents simultaneously. Each must produce a radically different approach.

- Agent 1: Minimize method count - aim for 1-3 methods max
- Agent 2: Maximize flexibility - support many use cases
- Agent 3: Optimize for the most common case

Each agent outputs:
1. Interface signature (types/methods)
2. Usage example (how caller uses it)
3. What this design hides internally
4. Trade-offs of this approach

### 3. Present Designs

Show each design with interface signature, usage examples, and what it hides. Present designs sequentially so user can absorb each approach before comparison.

### 4. Compare Designs

Compare on: interface simplicity, general-purpose vs specialized, implementation efficiency, depth, ease of correct use vs ease of misuse. Discuss trade-offs in prose, not tables.

### 5. Synthesize

Ask which design best fits the primary use case and whether any elements from other designs are worth incorporating.

## Anti-Patterns

- Do not let sub-agents produce similar designs - enforce radical difference
- Do not skip comparison - the value is in contrast
- Do not implement - this is purely about interface shape