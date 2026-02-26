#!/usr/bin/env python3
"""
Google Calendar operations CLI. Output: JSON.

Commands:
  list    --date YYYY-MM-DD [--days N]
  add     --title T --start DT --end DT [--description D] [--location L]
  modify  --event-id ID [--title T] [--start DT] [--end DT] [--description D] [--location L]
  free    --date YYYY-MM-DD [--duration MINS] [--range-start HH:MM] [--range-end HH:MM]
  search  --query TEXT [--days N]

DT format: ISO 8601 with offset, e.g. 2026-02-27T15:00:00-05:00
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']
SKILL_DIR = Path(__file__).parent.parent
CREDS_FILE = SKILL_DIR / 'credentials.json'
TOKEN_FILE = SKILL_DIR / 'token.json'


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(json.dumps({"error": f"credentials.json not found at {CREDS_FILE}. See SKILL.md for setup."}))
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def local_tz():
    return datetime.now().astimezone().tzinfo


def format_event(event):
    start = event.get('start', {})
    end = event.get('end', {})
    return {
        'id': event.get('id'),
        'title': event.get('summary', '(No title)'),
        'start': start.get('dateTime', start.get('date')),
        'end': end.get('dateTime', end.get('date')),
        'location': event.get('location', ''),
        'description': event.get('description', ''),
        'all_day': 'date' in start,
        'link': event.get('htmlLink', ''),
    }


def cmd_list(service, args):
    tz = local_tz()
    d = datetime.fromisoformat(args.date).replace(tzinfo=tz)
    start = d.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=args.days)

    result = service.events().list(
        calendarId='primary',
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime',
    ).execute()

    events = [format_event(e) for e in result.get('items', [])]
    print(json.dumps({'date': args.date, 'days': args.days, 'events': events, 'total': len(events)}, indent=2))


def cmd_add(service, args):
    start_dt = datetime.fromisoformat(args.start)
    end_dt = datetime.fromisoformat(args.end)

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=local_tz())
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=local_tz())

    event_body = {
        'summary': args.title,
        'start': {'dateTime': start_dt.isoformat()},
        'end': {'dateTime': end_dt.isoformat()},
    }
    if args.description:
        event_body['description'] = args.description
    if args.location:
        event_body['location'] = args.location

    event = service.events().insert(calendarId='primary', body=event_body).execute()
    print(json.dumps({'status': 'created', 'event': format_event(event)}, indent=2))


def cmd_modify(service, args):
    event = service.events().get(calendarId='primary', eventId=args.event_id).execute()

    if args.title:
        event['summary'] = args.title
    if args.start:
        start_dt = datetime.fromisoformat(args.start)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=local_tz())
        event['start'] = {'dateTime': start_dt.isoformat()}
    if args.end:
        end_dt = datetime.fromisoformat(args.end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=local_tz())
        event['end'] = {'dateTime': end_dt.isoformat()}
    if args.description:
        event['description'] = args.description
    if args.location:
        event['location'] = args.location

    updated = service.events().update(calendarId='primary', eventId=args.event_id, body=event).execute()
    print(json.dumps({'status': 'updated', 'event': format_event(updated)}, indent=2))


def cmd_free(service, args):
    tz = local_tz()
    d = datetime.fromisoformat(args.date)

    rsh, rsm = map(int, args.range_start.split(':'))
    reh, rem = map(int, args.range_end.split(':'))

    range_start = d.replace(hour=rsh, minute=rsm, second=0, microsecond=0, tzinfo=tz)
    range_end = d.replace(hour=reh, minute=rem, second=0, microsecond=0, tzinfo=tz)
    duration = timedelta(minutes=args.duration)

    body = {
        "timeMin": range_start.isoformat(),
        "timeMax": range_end.isoformat(),
        "items": [{"id": "primary"}],
    }
    result = service.freebusy().query(body=body).execute()
    busy_periods = result.get('calendars', {}).get('primary', {}).get('busy', [])

    cursor = range_start
    free_slots = []

    for period in busy_periods:
        ps = datetime.fromisoformat(period['start'])
        pe = datetime.fromisoformat(period['end'])

        if ps.tzinfo is None:
            ps = ps.replace(tzinfo=tz)
        if pe.tzinfo is None:
            pe = pe.replace(tzinfo=tz)

        ps = ps.astimezone(tz)
        pe = pe.astimezone(tz)

        gap = ps - cursor
        if gap >= duration:
            free_slots.append({
                'start': cursor.isoformat(),
                'end': ps.isoformat(),
                'duration_minutes': int(gap.total_seconds() / 60),
            })
        if pe > cursor:
            cursor = pe

    trailing = range_end - cursor
    if trailing >= duration:
        free_slots.append({
            'start': cursor.isoformat(),
            'end': range_end.isoformat(),
            'duration_minutes': int(trailing.total_seconds() / 60),
        })

    print(json.dumps({
        'date': args.date,
        'range': f"{args.range_start}-{args.range_end}",
        'duration_minutes': args.duration,
        'busy': busy_periods,
        'free_slots': free_slots,
    }, indent=2))


def cmd_search(service, args):
    tz = local_tz()
    now = datetime.now(tz=tz)
    end = now + timedelta(days=args.days)

    result = service.events().list(
        calendarId='primary',
        q=args.query,
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime',
    ).execute()

    events = [format_event(e) for e in result.get('items', [])]
    print(json.dumps({'query': args.query, 'events': events, 'total': len(events)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Google Calendar CLI')
    sub = parser.add_subparsers(dest='command')

    p_list = sub.add_parser('list')
    p_list.add_argument('--date', required=True, help='YYYY-MM-DD')
    p_list.add_argument('--days', type=int, default=1)

    p_add = sub.add_parser('add')
    p_add.add_argument('--title', required=True)
    p_add.add_argument('--start', required=True, help='ISO 8601 datetime')
    p_add.add_argument('--end', required=True, help='ISO 8601 datetime')
    p_add.add_argument('--description', default='')
    p_add.add_argument('--location', default='')

    p_mod = sub.add_parser('modify')
    p_mod.add_argument('--event-id', required=True)
    p_mod.add_argument('--title', default='')
    p_mod.add_argument('--start', default='')
    p_mod.add_argument('--end', default='')
    p_mod.add_argument('--description', default='')
    p_mod.add_argument('--location', default='')

    p_free = sub.add_parser('free')
    p_free.add_argument('--date', required=True, help='YYYY-MM-DD')
    p_free.add_argument('--duration', type=int, default=60, help='Desired free block in minutes')
    p_free.add_argument('--range-start', default='06:00', help='Start of search window HH:MM')
    p_free.add_argument('--range-end', default='22:00', help='End of search window HH:MM')

    p_search = sub.add_parser('search')
    p_search.add_argument('--query', required=True)
    p_search.add_argument('--days', type=int, default=30)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        service = get_service()
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    try:
        {
            'list': cmd_list,
            'add': cmd_add,
            'modify': cmd_modify,
            'free': cmd_free,
            'search': cmd_search,
        }[args.command](service, args)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
