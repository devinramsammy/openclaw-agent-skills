#!/usr/bin/env python3
"""
Fetch and classify Gmail emails from the past N hours.
Output: JSON with emails grouped by category.

Usage: python fetch_emails.py [hours_back]
"""

import json
import base64
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
                print(json.dumps({
                    "error": f"credentials.json not found at {CREDS_FILE}. See setup.md for instructions."
                }))
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def decode_part(part):
    data = part.get('body', {}).get('data', '')
    if not data:
        return ''
    return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')


def extract_text(payload):
    mime = payload.get('mimeType', '')

    if mime == 'text/plain':
        return decode_part(payload)

    if mime == 'text/html':
        html = decode_part(payload)
        text = re.sub(r'<[^>]+>', ' ', html)
        return re.sub(r'\s+', ' ', text).strip()

    for part in payload.get('parts', []):
        result = extract_text(part)
        if result:
            return result

    return ''


def extract_html(payload):
    mime = payload.get('mimeType', '')

    if mime == 'text/html':
        return decode_part(payload)

    for part in payload.get('parts', []):
        result = extract_html(part)
        if result:
            return result

    return ''


def extract_unsubscribe_links(headers, html_body):
    links = []

    for header in headers:
        if header['name'].lower() == 'list-unsubscribe':
            links += re.findall(r'<(https?://[^>]+)>', header['value'])
            links += re.findall(r'<(mailto:[^>]+)>', header['value'])

    if html_body:
        patterns = [
            r'href=["\']([^"\']*unsubscribe[^"\']*)["\']',
            r'href=["\']([^"\']*opt[-_]?out[^"\']*)["\']',
            r'href=["\']([^"\']*manage[-_]?preferences[^"\']*)["\']',
            r'href=["\']([^"\']*email[-_]?preferences[^"\']*)["\']',
        ]
        for pattern in patterns:
            found = re.findall(pattern, html_body, re.IGNORECASE)
            links.extend(found[:2])

    seen = set()
    deduped = []
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)

    return deduped[:3]


def classify(subject, sender, labels, preview, unsubscribe_links):
    if unsubscribe_links:
        return 'newsletter'

    if 'IMPORTANT' in labels or 'STARRED' in labels:
        return 'important'

    if 'CATEGORY_PROMOTIONS' in labels:
        return 'promotional'

    if 'CATEGORY_SOCIAL' in labels:
        return 'social'

    return 'general'


def fetch_emails(hours_back=24, max_results=150):
    service = get_service()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    query = f'after:{int(cutoff.timestamp())}'

    result = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results,
    ).execute()

    message_refs = result.get('messages', [])
    emails = []

    for ref in message_refs:
        msg = service.users().messages().get(
            userId='me',
            id=ref['id'],
            format='full',
        ).execute()

        headers = msg['payload'].get('headers', [])
        hmap = {h['name'].lower(): h['value'] for h in headers}

        subject = hmap.get('subject', '(no subject)')
        sender = hmap.get('from', '')
        date_str = hmap.get('date', '')
        snippet = msg.get('snippet', '')
        labels = msg.get('labelIds', [])

        html_body = extract_html(msg['payload'])
        text_body = extract_text(msg['payload'])
        preview = (text_body or snippet)[:400]

        unsubscribe_links = extract_unsubscribe_links(headers, html_body)
        category = classify(subject, sender, labels, preview, unsubscribe_links)

        emails.append({
            'id': msg['id'],
            'subject': subject,
            'from': sender,
            'date': date_str,
            'snippet': snippet,
            'preview': preview,
            'category': category,
            'unsubscribe_links': unsubscribe_links,
            'labels': labels,
            'is_unread': 'UNREAD' in labels,
        })

    return emails


def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24

    try:
        emails = fetch_emails(hours_back=hours)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    by_category = {}
    for email in emails:
        by_category.setdefault(email['category'], []).append(email)

    output = {
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'hours_back': hours,
        'total': len(emails),
        'counts_by_category': {cat: len(items) for cat, items in by_category.items()},
        'emails': emails,
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
