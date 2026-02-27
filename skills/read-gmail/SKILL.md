---
name: read-gmail
description: Reads and analyzes Gmail inbox with persistent memory. Provides daily email digests, scores emails using LLM judgment + saved preferences, and surfaces unsubscribe links. Updates memory after each session based on user decisions. Use when asked to check email, read Gmail, provide an email digest, find unsubscribe links, review inbox, or manage inbox preferences. NEVER sends, replies, drafts, or modifies emails.
---

# Read Gmail

## Setup (first-time only)

Use a Python virtual environment when installing packages.

**If `.venv` already exists:** just activate it:

```bash
cd skills/read-gmail
source .venv/bin/activate
```

**If not:** create it, then activate and install:

```bash
cd skills/read-gmail
python -m venv .venv
source .venv/bin/activate
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client pyyaml
```

`credentials.json` must be present in `skills/read-gmail/`. On first run a browser window opens for OAuth consent — `token.json` is saved automatically after.

## Workflow

Copy this checklist and check off steps as you complete them:

```
- [ ] 1. Load context (email-interests.md + memory.yml)
- [ ] 2. Fetch emails
- [ ] 3. Score each email
- [ ] 4. Present digest
- [ ] 5. Ask about uncertain emails (score 3)
- [ ] 6. Update memory and interests
```

### 1. Load context

Read `skills/read-gmail/email-interests.md` and `skills/read-gmail/memory.yml`.

- `email-interests.md` — Topics user is interested in. Primary lens for scoring.
- `memory.yml` — `keep`/`remove` rules (match against `from` or `subject`) and past `decisions`.

### 2. Fetch emails

```bash
python skills/read-gmail/scripts/fetch_emails.py [hours_back]
```

Outputs JSON `emails[]` with: `subject`, `from`, `date`, `snippet`, `preview`, `category`, `unsubscribe_links`, `is_unread`.

### 3. Score each email

**Memory rules first (deterministic):**

- `keep` match → KEEP
- `remove` match → REMOVE

**Everything else — LLM judgment using `email-interests.md`:**

Score 1–5:

- **5** — time-sensitive, personal, known contact
- **4** — relevant to their work/interests
- **3** — uncertain
- **2** — generic, off-topic, low-signal
- **1** — mass outreach, irrelevant promo, spam-adjacent

Signals to weigh: personalization, sender reputation, relevance to interests, urgency.

### 4. Digest

```
## Email Digest — [Date]
[X] emails · [Y] unread · past [Z] hours

### Action Required / Important
- **[Subject]** · [Sender] · [date]
  [2–3 sentences.]

### Worth a Look
- **[Subject]** · [Sender] — [1 sentence]
  [If unsubscribe link present: Unsubscribe: [exact URL]]

### Unsubscribe Candidates
Only include if an unsubscribe link is present in the email. Always display the full link verbatim — never omit or truncate it.
- **[Sender]** — [Subject]
  Unsubscribe: [exact URL]

### Noise
• [Sender] — [Subject]  • [Sender] — [Subject] ...
```

Skip empty sections.

### 5. Ask about uncertain emails

List score-3 emails and ask the user what to do with them so memory can be updated.

### 6. Update memory and interests

**Structured decisions → `memory.yml`:**

```bash
# One-off decision
python skills/read-gmail/scripts/update_memory.py \
  --decision '{"action":"remove","sender":"deals@grubhub.com","subject":"$5 off","reason":"not relevant"}'

# Persistent keep rule
python skills/read-gmail/scripts/update_memory.py --keep "stripe.com" --type domain --reason "Billing"

# Persistent remove rule
python skills/read-gmail/scripts/update_memory.py --remove "linkedin.com" --type domain --reason "Noise"
```

`remove` decisions are auto-promoted to persistent rules.

**Preference signals → `email-interests.md`:**

After each session, if the user reveals anything new about themselves — topics they care about, senders they like or hate, context about their job or habits — append it as a plain note to `email-interests.md`. No specific format required, just write what was learned.

Examples of things worth appending:

- "User said they don't care about NBA game updates"
- "User said Grubhub emails are always noise"

This keeps scoring accuracy improving over time without the user having to manually maintain the file.

## Constraints

- NEVER send, reply, forward, draft, compose, modify labels, mark as read, archive, or delete
- Show unsubscribe links verbatim — never follow them
