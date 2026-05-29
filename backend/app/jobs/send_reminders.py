"""Individual reminder cron job.

Sends plain-text reminders for todos and events whose remind_at has
passed and remind_sent is still false. Marks each as sent on success;
leaves failures untouched so they retry on the next pass.

Entrypoint: python -m app.jobs.send_reminders
Railway schedule: cron */15 * * * * (every 15 minutes).

Delivery notes:
  - Uses send_text, which only works inside the 24-hour window opened by
    the morning digest. On failure the row is retried automatically on
    the next 15-minute pass once the window reopens.
  - Rows whose owner has recordatorios disabled are skipped but NOT
    marked sent. This is intentional: if the user re-enables the module,
    pending due reminders flush on the next cron pass (same self-healing
    behavior as window-closed failures). Reminders that become far past
    due during a long disable period will fire as a burst on re-enable.
"""
import warnings
from datetime import datetime, timezone

from app.db import client
from app.notify import send_text


def _recordatorios_enabled(user_id: str) -> bool:
    result = (
        client.table("user_modules")
        .select("enabled")
        .eq("user_id", user_id)
        .eq("module", "recordatorios")
        .execute()
    )
    rows = result.data or []
    if not rows:
        return True
    return bool(rows[0]["enabled"])


def _due_rows(table: str, title_field: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table(table)
        .select(f"id, user_id, {title_field}")
        .eq("remind_sent", False)
        .lte("remind_at", now)
        .execute()
    )
    return result.data or []


def _phone_for_user(user_id: str) -> str | None:
    result = (
        client.table("users")
        .select("phone")
        .eq("id", user_id)
        .execute()
    )
    rows = result.data or []
    return rows[0]["phone"] if rows else None


def _mark_sent(table: str, row_id: str) -> None:
    client.table(table).update({"remind_sent": True}).eq("id", row_id).execute()


def main() -> None:
    sent = 0
    failed = 0
    skipped = 0

    for table, title_field in [("todos", "task"), ("events", "title")]:
        for row in _due_rows(table, title_field):
            user_id = row["user_id"]

            if not _recordatorios_enabled(user_id):
                skipped += 1
                continue

            phone = _phone_for_user(user_id)
            if not phone:
                skipped += 1
                continue

            title = row[title_field]
            ok = send_text(phone, f"⏰ {title}")
            if ok:
                _mark_sent(table, row["id"])
                sent += 1
            else:
                failed += 1

    warnings.warn(
        f"send_reminders complete: sent={sent} failed={failed} skipped={skipped}",
        stacklevel=1,
    )


if __name__ == "__main__":
    main()
