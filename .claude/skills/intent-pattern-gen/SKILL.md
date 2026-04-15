---
name: intent-pattern-gen
description: >
  Given a feature name and example Spanish WhatsApp messages,
  generates the manual-mode regex pattern(s) and an AI-mode
  prompt fragment for that intent. Use when adding a new command
  to the router.
argument-hint: "<feature> — example messages separated by semicolons"
agent: sub
---

You are generating intent patterns for Cazuela's WhatsApp router.
Cazuela parses Spanish natural language messages and routes them
to feature handlers.

DO NOT write any files. Output the patterns as code blocks
for the developer to review.

## Step 1 — Read existing patterns

Read `backend/app/router.py` in full before generating anything.
Understand the naming conventions, regex style, and how patterns
are ordered and tested.

## Step 2 — Understand the argument

The argument gives the feature name and example messages.
Example:
`reminders — recordarme tomar la pastilla a las 9;
recuérdame llamar al médico mañana;
avísame cuando sean las 6`

If no argument is given, ask the user for the feature name
and at least 3 example messages before proceeding.

## Step 3 — Generate outputs

### Output 1: Regex pattern(s)

One or more `re.compile` patterns that together capture the
examples provided. For each pattern:
- Named `FEATURE_ACTION_PATTERN` following router.py conventions
- Uses `re.IGNORECASE`
- Handles accented and unaccented variants
  (e.g. `recuerd[ae]me`, `aví[sz]ame`)
- Captures the meaningful part (time, task, date) in a group
- Anchored with `^` and `$` where the message is a full command;
  left-anchored only where trailing content is expected

### Output 2: Example matches table

A markdown table showing which of the provided example messages
each pattern matches and what each capture group contains.
This helps the developer verify the regex is correct before
adding it.

### Output 3: Edge cases to watch

2-4 bullet points describing messages that look similar but
should NOT match (to help avoid false positives against
existing patterns).

### Output 4: AI-mode prompt fragment

A short paragraph (3-5 sentences) describing this intent
for use in a future AI-mode system prompt. Explains:
- What the user is trying to do
- What structured data to extract (fields and types)
- How to handle ambiguity

## Rules

- Prefer simpler regex over clever regex — readability matters
- Do not generate patterns that would conflict with existing ones
  in router.py (flag any potential conflicts explicitly)
- Keep the AI-mode fragment concise — it will be concatenated
  with other intent descriptions
- If the examples are too vague to generate a reliable pattern,
  ask for more examples before proceeding
