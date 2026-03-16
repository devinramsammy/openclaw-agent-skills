#!/usr/bin/env python3
"""
Manage a SQLite-backed todo list.

Usage:
  python3 todo.py add --title "Buy groceries" [--description "..."]
  python3 todo.py list [--status open|finished|all]
  python3 todo.py done <id>
  python3 todo.py reopen <id>
  python3 todo.py delete <id>
  python3 todo.py update <id> [--title "..."] [--description "..."]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "todo.db"
VALID_STATUSES = {"open", "finished"}
LIST_STATUSES = sorted(VALID_STATUSES | {"all"})


class TodoError(Exception):
    """Raised when a todo operation cannot be completed."""


def main() -> None:
    args = parse_args(sys.argv[1:])

    try:
        result = run_command(args)
    except TodoError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage a SQLite-backed todo list.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a todo.")
    add_parser.add_argument("--title", required=True, help="Todo title.")
    add_parser.add_argument(
        "--description",
        default="",
        help="Optional todo description.",
    )

    list_parser = subparsers.add_parser("list", help="List todos.")
    list_parser.add_argument(
        "--status",
        default="open",
        choices=LIST_STATUSES,
        help="Filter by status.",
    )

    for command_name in ("done", "reopen", "delete"):
        command_parser = subparsers.add_parser(command_name, help=f"{command_name.title()} a todo.")
        command_parser.add_argument("todo_id", type=int, help="Todo ID.")

    update_parser = subparsers.add_parser("update", help="Update a todo's title or description.")
    update_parser.add_argument("todo_id", type=int, help="Todo ID.")
    update_parser.add_argument("--title", help="New title (optional).")
    update_parser.add_argument("--description", help="New description (optional).")

    return parser.parse_args(argv)


def run_command(args: argparse.Namespace) -> dict | list[dict]:
    connection = connect()
    try:
        if args.command == "add":
            return add_todo(connection, args.title, args.description)

        if args.command == "list":
            return list_todos(connection, args.status)

        if args.command == "done":
            return update_status(connection, args.todo_id, "finished")

        if args.command == "reopen":
            return update_status(connection, args.todo_id, "open")

        if args.command == "delete":
            return delete_todo(connection, args.todo_id)

        if args.command == "update":
            return update_todo(
                connection,
                args.todo_id,
                title=args.title,
                description=args.description,
            )

        raise TodoError(f"Unknown command: {args.command}")
    finally:
        connection.close()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'finished'))
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)"
    )
    connection.commit()


def add_todo(
    connection: sqlite3.Connection,
    title: str,
    description: str,
) -> dict:
    normalized_title = title.strip()
    if not normalized_title:
        raise TodoError("Title cannot be empty.")

    cursor = connection.execute(
        """
        INSERT INTO todos (title, description)
        VALUES (?, ?)
        """,
        (normalized_title, description.strip()),
    )
    connection.commit()
    return fetch_todo(connection, cursor.lastrowid)


def list_todos(
    connection: sqlite3.Connection,
    status: str,
) -> list[dict]:
    if status == "all":
        rows = connection.execute(
            """
            SELECT id, title, description, status
            FROM todos
            ORDER BY
                CASE status WHEN 'open' THEN 0 ELSE 1 END,
                id ASC
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, title, description, status
            FROM todos
            WHERE status = ?
            ORDER BY id ASC
            """,
            (status,),
        ).fetchall()

    return [row_to_dict(row) for row in rows]


def update_todo(
    connection: sqlite3.Connection,
    todo_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
) -> dict:
    ensure_todo_exists(connection, todo_id)
    if title is None and description is None:
        raise TodoError("Provide at least one of --title or --description.")

    updates = []
    params = []
    if title is not None:
        normalized = title.strip()
        if not normalized:
            raise TodoError("Title cannot be empty.")
        updates.append("title = ?")
        params.append(normalized)
    if description is not None:
        updates.append("description = ?")
        params.append(description.strip())

    params.append(todo_id)
    connection.execute(
        f"UPDATE todos SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    connection.commit()
    return fetch_todo(connection, todo_id)


def update_status(
    connection: sqlite3.Connection,
    todo_id: int,
    status: str,
) -> dict:
    ensure_valid_status(status)
    ensure_todo_exists(connection, todo_id)

    connection.execute(
        """
        UPDATE todos
        SET status = ?
        WHERE id = ?
        """,
        (status, todo_id),
    )
    connection.commit()
    return fetch_todo(connection, todo_id)


def delete_todo(connection: sqlite3.Connection, todo_id: int) -> dict:
    todo = fetch_todo(connection, todo_id)
    connection.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    connection.commit()
    return {
        "deleted": True,
        "todo": todo,
    }


def fetch_todo(connection: sqlite3.Connection, todo_id: int) -> dict:
    row = connection.execute(
        """
        SELECT id, title, description, status
        FROM todos
        WHERE id = ?
        """,
        (todo_id,),
    ).fetchone()

    if row is None:
        raise TodoError(f"Todo {todo_id} not found.")

    return row_to_dict(row)


def ensure_todo_exists(connection: sqlite3.Connection, todo_id: int) -> None:
    connection.execute(
        "SELECT 1 FROM todos WHERE id = ?",
        (todo_id,),
    ).fetchone() or raise_not_found(todo_id)


def ensure_valid_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise TodoError(
            f"Invalid status '{status}'. Valid statuses: {', '.join(sorted(VALID_STATUSES))}"
        )


def raise_not_found(todo_id: int) -> None:
    raise TodoError(f"Todo {todo_id} not found.")


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
    }


if __name__ == "__main__":
    main()
