---
name: ubiquitous-language
description: Extract a DDD-style ubiquitous language glossary from the current conversation, flagging ambiguities and proposing canonical terms. Saves to UBIQUITOUS_LANGUAGE.md. Use when user wants to define domain terms, build a glossary, harden terminology, create a ubiquitous language, or mentions "domain model" or "DDD".
version: 1.0.0
author: mattpocock
---

# Ubiquitous Language

Extract and formalize domain terminology from the current conversation into a consistent glossary, saved to a local file.

## Process

1. Scan the conversation for domain-relevant nouns, verbs, and concepts
2. Identify problems: same word used for different concepts (ambiguity), different words used for the same concept (synonyms), vague or overloaded terms
3. Propose a canonical glossary with opinionated term choices
4. Write to UBIQUITOUS_LANGUAGE.md in the working directory
5. Output a summary inline in the conversation

## Output Format

Write a UBIQUITOUS_LANGUAGE.md file with term tables grouped by domain area, relationships section, example dialogue, and flagged ambiguities.

## Rules

- Be opinionated. When multiple words exist for the same concept, pick the best one and list the others as aliases to avoid.
- Flag conflicts explicitly. If a term is used ambiguously, call it out with a clear recommendation.
- Only include terms relevant for domain experts. Skip module or class names unless they have domain meaning.
- Keep definitions tight. One sentence max. Define what it IS, not what it does.
- Show relationships. Use bold term names and express cardinality where obvious.
- Group terms into multiple tables when natural clusters emerge.
- Write an example dialogue. A short conversation (3-5 exchanges) between a dev and a domain expert.

## Re-running

When invoked again in the same conversation:

1. Read the existing UBIQUITOUS_LANGUAGE.md
2. Incorporate any new terms from subsequent discussion
3. Update definitions if understanding has evolved
4. Re-flag any new ambiguities
5. Rewrite the example dialogue to incorporate new terms