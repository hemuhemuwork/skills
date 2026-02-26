#!/usr/bin/env python3
"""
Google Calendar CLI - Google Calendar API v3を使用した予定管理ツール

Usage:
    gcal.py auth                                    # OAuth初回認証
    gcal.py events --start <date> --end <date>      # 予定一覧
    gcal.py busy --start <date> --end <date>        # busy/freeサマリー
    gcal.py create --summary <title> --start <dt> --end <dt>  # 予定作成

Date formats: today, tomorrow, YYYY-MM-DD, +Nd (e.g. +7d)

Credentials are stored in the directory specified by GOOGLE_CREDENTIALS_DIR
in the skill's .env file (default: ~/.config/google-calendar/).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / ".env"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

DEFAULT_CREDS_DIR = Path.home() / ".config" / "google-calendar"


def load_dotenv():
    """Load skill-local .env file into os.environ."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if m:
            key, val = m.group(1), m.group(2)
            val = val.strip("'\"")
            os.environ.setdefault(key, val)


def get_creds_dir() -> Path:
    """Get credentials directory from .env or default."""
    load_dotenv()
    d = os.environ.get("GOOGLE_CREDENTIALS_DIR")
    if d:
        return Path(d).expanduser()
    return DEFAULT_CREDS_DIR


def get_credentials_file() -> Path:
    return get_creds_dir() / "credentials.json"


def get_token_file() -> Path:
    return get_creds_dir() / "token.json"


def parse_date(date_str: str) -> datetime:
    """Parse flexible date string to datetime."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str == "today":
        return today
    if date_str == "tomorrow":
        return today + timedelta(days=1)
    m = re.match(r"^\+(\d+)d$", date_str)
    if m:
        return today + timedelta(days=int(m.group(1)))
    return datetime.strptime(date_str, "%Y-%m-%d")


def get_credentials():
    """Get or refresh OAuth credentials."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_file = get_token_file()
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    return creds


def cmd_auth(_args):
    """Run OAuth authorization flow."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_dir = get_creds_dir()
    creds_file = get_credentials_file()
    token_file = get_token_file()

    creds_dir.mkdir(parents=True, exist_ok=True)

    if not creds_file.exists():
        print(f"Error: {creds_file} not found.", file=sys.stderr)
        print("Download OAuth client ID JSON from Google Cloud Console", file=sys.stderr)
        print(f"and place it at: {creds_file}", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=8080)
    token_file.write_text(creds.to_json())
    token_file.chmod(0o600)
    print(f"Authentication successful. Token saved to {token_file}")


def cmd_events(args):
    """List events in a date range."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    if not creds or not creds.valid:
        print("Error: Not authenticated. Run 'gcal.py auth' first.", file=sys.stderr)
        sys.exit(1)

    service = build("calendar", "v3", credentials=creds)

    start_dt = parse_date(args.start)
    end_dt = parse_date(args.end) + timedelta(days=1)  # inclusive end
    calendar_id = args.calendar_id or "primary"

    time_min = start_dt.isoformat() + "Z"
    time_max = end_dt.isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    output = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        output.append(
            {
                "summary": event.get("summary", "(No title)"),
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "description": event.get("description", ""),
                "htmlLink": event.get("htmlLink", ""),
            }
        )

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_busy(args):
    """Get busy/free summary for a date range."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    if not creds or not creds.valid:
        print("Error: Not authenticated. Run 'gcal.py auth' first.", file=sys.stderr)
        sys.exit(1)

    service = build("calendar", "v3", credentials=creds)

    start_dt = parse_date(args.start)
    end_dt = parse_date(args.end) + timedelta(days=1)
    calendar_id = args.calendar_id or "primary"

    body = {
        "timeMin": start_dt.isoformat() + "Z",
        "timeMax": end_dt.isoformat() + "Z",
        "items": [{"id": calendar_id}],
    }

    result = service.freebusy().query(body=body).execute()
    calendars = result.get("calendars", {})
    busy_times = calendars.get(calendar_id, {}).get("busy", [])

    output = {
        "calendar": calendar_id,
        "range": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
        "busy": busy_times,
        "busyCount": len(busy_times),
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_create(args):
    """Create a new calendar event."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    if not creds or not creds.valid:
        print("Error: Not authenticated. Run 'gcal.py auth' first.", file=sys.stderr)
        sys.exit(1)

    service = build("calendar", "v3", credentials=creds)
    calendar_id = args.calendar_id or "primary"
    timezone = args.timezone

    event_body = {
        "summary": args.summary,
        "start": {"dateTime": args.start, "timeZone": timezone},
        "end": {"dateTime": args.end, "timeZone": timezone},
    }
    if args.description:
        event_body["description"] = args.description
    if args.location:
        event_body["location"] = args.location

    event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    print(json.dumps({
        "status": "created",
        "id": event["id"],
        "summary": event.get("summary"),
        "start": event["start"],
        "end": event["end"],
        "htmlLink": event.get("htmlLink", ""),
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Google Calendar CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # auth
    subparsers.add_parser("auth", help="Run OAuth authorization")

    # events
    events_parser = subparsers.add_parser("events", help="List events")
    events_parser.add_argument("--start", required=True, help="Start date")
    events_parser.add_argument("--end", required=True, help="End date")
    events_parser.add_argument("--calendar-id", help="Calendar ID (default: primary)")

    # busy
    busy_parser = subparsers.add_parser("busy", help="Get busy/free summary")
    busy_parser.add_argument("--start", required=True, help="Start date")
    busy_parser.add_argument("--end", required=True, help="End date")
    busy_parser.add_argument("--calendar-id", help="Calendar ID (default: primary)")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new event")
    create_parser.add_argument("--summary", required=True, help="Event title")
    create_parser.add_argument("--start", required=True, help="Start datetime (ISO 8601)")
    create_parser.add_argument("--end", required=True, help="End datetime (ISO 8601)")
    create_parser.add_argument("--timezone", default="Asia/Tokyo", help="Timezone (default: Asia/Tokyo)")
    create_parser.add_argument("--description", help="Event description")
    create_parser.add_argument("--location", help="Event location")
    create_parser.add_argument("--calendar-id", help="Calendar ID (default: primary)")

    args = parser.parse_args()

    commands = {"auth": cmd_auth, "events": cmd_events, "busy": cmd_busy, "create": cmd_create}
    commands[args.command](args)


if __name__ == "__main__":
    main()
