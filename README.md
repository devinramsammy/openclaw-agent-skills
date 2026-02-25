# agent-skills

My personal OpenClaw skills.

---

## read-gmail

Reads and analyzes Gmail

| File                 | Purpose                        |
| -------------------- | ------------------------------ |
| `credentials.json`   | OAuth client from Google Cloud |
| `token.json`         | Auto-generated on first run    |
| `email-interests.md` | Your email preferences         |

---

## smart-lights

Control Govee lights and plugs (on/off, brightness) via the Govee Open API

| File                      | Purpose                                                                   |
| ------------------------- | ------------------------------------------------------------------------- |
| `.env`                    | `GOVEE_API_KEY` — get from [Govee Developer](https://developer.govee.com) |
| `devices.json`            | Cached device list                                                        |
| `scripts/govee_client.py` | CLI and Python client                                                     |
