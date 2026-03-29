"""
Migrate existing request data to deduplicate system-reminder content.

WARNING: This script modifies existing data. Make a backup first!

Run: python scripts/deduplicate_existing_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_PATH
from storage.database import Database
from proxy.anthropic_handler import AnthropicHandler

def extract_system_reminder(text: str):
    """Extract system-reminder block from text."""
    if "<system-reminder>" not in text:
        return text, None

    pattern = r'<system-reminder>.*?</system-reminder>'
    matches = re.findall(pattern, text, re.DOTALL)

    if not matches:
        return text, None

    cleaned = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    system_content = '\n'.join(matches)

    return cleaned, system_content


def process_request_batch(db: Database, offset: int, batch_size: int = 100):
    """Process a batch of requests."""
    with db.db_session() as session:
        from storage.models import Request

        requests = session.query(Request).order_by(Request.id).offset(offset).limit(batch_size).all()

        processed = 0
        deduplicated = 0
        bytes_saved = 0

        for req in requests:
            try:
                # Process request_body
                if req.request_body:
                    try:
                        body = json.loads(req.request_body)
                        original_len = len(req.request_body)

                        # Check if already processed
                        if "[SYSTEM_REMINDER_REF:" in req.request_body:
                            continue

                        # Process messages in body
                        if "messages" in body:
                            messages = body.get("messages", [])
                            for msg in messages:
                                if msg.get("role") != "user":
                                    continue

                                content = msg.get("content", "")
                                if isinstance(content, list):
                                    for block in content:
                                        if block.get("type") == "text":
                                            text = block.get("text", "")
                                            cleaned, system_reminder = extract_system_reminder(text)
                                            if system_reminder:
                                                content_hash = db.save_system_reminder(system_reminder)
                                                block["text"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()
                                                deduplicated += 1
                                elif isinstance(content, str):
                                    cleaned, system_reminder = extract_system_reminder(content)
                                    if system_reminder:
                                        content_hash = db.save_system_reminder(system_reminder)
                                        msg["content"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()
                                        deduplicated += 1

                        new_body = json.dumps(body)
                        req.request_body = new_body
                        bytes_saved += (original_len - len(new_body))

                    except json.JSONDecodeError:
                        pass

                # Process messages_json
                if req.messages_json and "[SYSTEM_REMINDER_REF:" not in req.messages_json:
                    try:
                        messages = json.loads(req.messages_json)
                        original_len = len(req.messages_json)

                        for msg in messages:
                            if msg.get("role") != "user":
                                continue

                            content = msg.get("content", "")
                            if isinstance(content, list):
                                for block in content:
                                    if block.get("type") == "text":
                                        text = block.get("text", "")
                                        cleaned, system_reminder = extract_system_reminder(text)
                                        if system_reminder:
                                            content_hash = db.save_system_reminder(system_reminder)
                                            block["text"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()
                            elif isinstance(content, str):
                                cleaned, system_reminder = extract_system_reminder(content)
                                if system_reminder:
                                    content_hash = db.save_system_reminder(system_reminder)
                                    msg["content"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()

                        new_messages = json.dumps(messages)
                        req.messages_json = new_messages
                        bytes_saved += (original_len - len(new_messages))

                    except json.JSONDecodeError:
                        pass

                processed += 1

            except Exception as e:
                print(f"  Error processing {req.request_id}: {e}")
                continue

        session.commit()
        return processed, deduplicated, bytes_saved


def main():
    """Main migration function."""
    db = Database()

    # Get total count
    with db.db_session() as session:
        from storage.models import Request
        total = session.query(Request).count()

    if total == 0:
        print("No requests to process.")
        return

    print(f"Processing {total} requests...")
    print("This may take a while. Press Ctrl+C to stop (progress will be saved).\n")

    batch_size = 100
    offset = 0
    total_processed = 0
    total_deduplicated = 0
    total_bytes_saved = 0

    try:
        while offset < total:
            processed, deduplicated, bytes_saved = process_request_batch(db, offset, batch_size)

            if processed == 0:
                break

            total_processed += processed
            total_deduplicated += deduplicated
            total_bytes_saved += bytes_saved

            print(f"  Processed {total_processed}/{total} | "
                  f"Deduplicated: {total_deduplicated} | "
                  f"Saved: {total_bytes_saved / 1024 / 1024:.2f} MB")

            offset += batch_size

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress saved.")

    # Show final stats
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Total requests processed: {total_processed}")
    print(f"Total system-reminders deduplicated: {total_deduplicated}")
    print(f"Total bytes saved: {total_bytes_saved / 1024 / 1024:.2f} MB")

    stats = db.get_system_reminder_stats()
    print(f"\nDeduplication Stats:")
    print(f"  Unique system-reminders: {stats['unique_count']}")
    print(f"  Total uses: {stats['total_uses']}")
    print(f"  Space saved: {stats['savings_bytes'] / 1024 / 1024:.2f} MB ({stats['savings_percent']:.1f}%)")


if __name__ == "__main__":
    main()
