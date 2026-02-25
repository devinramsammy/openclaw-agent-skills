#!/usr/bin/env python3
"""
Update memory.yml with new decisions from the agent.

Usage:
  python update_memory.py --decision '<JSON>'
  python update_memory.py --keep '<pattern>' --type domain --reason '<reason>'
  python update_memory.py --remove '<pattern>' --type domain --reason '<reason>'
  python update_memory.py --context '<new context text>'

Decision JSON format:
  {"action": "keep|remove|unsure", "sender": "...", "subject": "...", "reason": "..."}
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).parent.parent
MEMORY_FILE = SKILL_DIR / 'memory.yml'


def load_memory():
    if not MEMORY_FILE.exists():
        return {'keep': [], 'remove': [], 'context': '', 'decisions': []}
    with open(MEMORY_FILE) as f:
        return yaml.safe_load(f) or {}


def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        yaml.dump(memory, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def ensure_list(memory, key):
    if not isinstance(memory.get(key), list):
        memory[key] = []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--decision', help='JSON string: {action, sender, subject, reason}')
    parser.add_argument('--keep', help='Add a pattern to the keep list')
    parser.add_argument('--remove', help='Add a pattern to the remove list')
    parser.add_argument('--type', default='domain', help='Pattern type: domain | sender | subject_contains')
    parser.add_argument('--reason', default='', help='Reason for this rule')
    parser.add_argument('--context', help='Replace the context notes')
    args = parser.parse_args()

    memory = load_memory()
    ensure_list(memory, 'keep')
    ensure_list(memory, 'remove')
    ensure_list(memory, 'decisions')

    changed = False

    if args.decision:
        try:
            d = json.loads(args.decision)
        except json.JSONDecodeError as e:
            print(f"Error parsing decision JSON: {e}", file=sys.stderr)
            sys.exit(1)

        d['date'] = str(date.today())
        memory['decisions'].append(d)

        # Auto-promote repeated remove decisions into persistent rules
        sender = d.get('sender', '')
        action = d.get('action', '')
        if action == 'remove' and sender:
            existing = [r.get('pattern', '') for r in memory['remove']]
            if sender not in existing:
                memory['remove'].append({
                    'pattern': sender,
                    'type': 'sender',
                    'reason': d.get('reason', 'Marked for removal'),
                })

        changed = True

    if args.keep:
        existing = [r.get('pattern', '') for r in memory['keep']]
        if args.keep not in existing:
            memory['keep'].append({
                'pattern': args.keep,
                'type': args.type,
                'reason': args.reason,
            })
            changed = True

    if args.remove:
        existing = [r.get('pattern', '') for r in memory['remove']]
        if args.remove not in existing:
            memory['remove'].append({
                'pattern': args.remove,
                'type': args.type,
                'reason': args.reason,
            })
            changed = True

    if args.context is not None:
        memory['context'] = args.context
        changed = True

    if changed:
        save_memory(memory)
        print(json.dumps({"status": "ok", "memory_file": str(MEMORY_FILE)}))
    else:
        print(json.dumps({"status": "no_change"}))


if __name__ == '__main__':
    main()
