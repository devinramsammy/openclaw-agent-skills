---
name: managing-todos
description: Manages a SQLite-backed todo list — add tasks, list open or finished items, mark done, reopen, delete, or update. Use when the user asks to add a todo, see their task list, check off an item, reopen a task, delete a todo, or edit a todo's title/description.
---

# Todo List

## Commands

No install needed — stdlib only.

**Add:**

```bash
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py add --title "Buy groceries" [--description "Milk, eggs, bread"]
```

**List** (defaults to `open`):

```bash
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py list [--status open|finished|all]
```

**Done / Reopen / Delete / Update:**

```bash
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py done TODO_ID
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py reopen TODO_ID
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py delete TODO_ID
python3 $HOME/.openclaw/skills/manage-todos/scripts/todo.py update TODO_ID [--title "..."] [--description "..."]
```

## Output

For `list`, always run with `--status open` and respond with a ordered list of open todos only:

```
1. Buy groceries — Milk, eggs, bread
2. Call dentist
```

If there are no open todos, say: `No todos.`

For `add`, `done`, `reopen`, and `update`, confirm with a single line: `✓ [action]: [title]` (e.g. `✓ Added: Buy groceries`). For `delete` say: `Deleted todo [ID].`

## Constraints

- Always list only `open` todos; never show `finished` items unless the user explicitly asks
- `status` is `open` or `finished`; default filter is `open`
- DB lives at `$HOME/.openclaw/skills/manage-todos/todo.db`, auto-created on first run
- `status` column is indexed for fast filtering
