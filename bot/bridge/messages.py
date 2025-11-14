from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


@dataclass(slots=True)
class BridgeMessageAttachmentMetadata:
    """Store attachment summary information for mirrored messages."""

    image_filename: Optional[str]
    notes: List[str]

    def to_record(self) -> dict[str, object]:
        return {
            "image_filename": self.image_filename,
            "notes": list(self.notes),
        }

    @classmethod
    def from_record(cls, record: Optional[dict]) -> "BridgeMessageAttachmentMetadata":
        if not record:
            return cls(image_filename=None, notes=[])
        return cls(
            image_filename=record.get("image_filename"),
            notes=list(record.get("notes") or []),
        )


@dataclass(slots=True)
class BridgeMessageRecord:
    """Persist metadata required to synchronise bridge messages."""

    source_id: int
    destination_ids: List[int]
    profile_seed: str
    display_name: str
    avatar_url: str
    dicebear_failed: bool
    attachments: BridgeMessageAttachmentMetadata
    updated_at: datetime

    def to_record(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "destination_ids": list(self.destination_ids),
            "profile_seed": self.profile_seed,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "dicebear_failed": self.dicebear_failed,
            "image_filename": self.attachments.image_filename,
            "attachment_notes": list(self.attachments.notes),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_record(cls, record: dict) -> "BridgeMessageRecord":
        attachments = BridgeMessageAttachmentMetadata.from_record(
            {
                "image_filename": record.get("image_filename"),
                "notes": record.get("attachment_notes"),
            }
        )
        return cls(
            source_id=int(record["source_id"]),
            destination_ids=[int(value) for value in record.get("destination_ids", [])],
            profile_seed=str(record.get("profile_seed", "")),
            display_name=str(record.get("display_name", "")),
            avatar_url=str(record.get("avatar_url", "")),
            dicebear_failed=bool(record.get("dicebear_failed", False)),
            attachments=attachments,
            updated_at=_parse_datetime(record.get("updated_at")),
        )


class BridgeMessageStore:
    """Persist bridge message metadata for later synchronisation."""

    def __init__(self, pool: ConnectionPool, table_name: str = "bridge_messages") -> None:
        self._pool = pool
        self._table_name = table_name

    def upsert(
        self,
        *,
        source_id: int,
        destination_ids: Iterable[int],
        profile_seed: str,
        display_name: str,
        avatar_url: str,
        dicebear_failed: bool,
        attachments: BridgeMessageAttachmentMetadata,
    ) -> None:
        normalized_destination_ids = _normalize_destination_ids(destination_ids)
        attachment_payload = attachments.to_record()
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._table_name} (
                        source_id,
                        destination_ids,
                        profile_seed,
                        display_name,
                        avatar_url,
                        dicebear_failed,
                        image_filename,
                        attachment_notes,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
                    ON CONFLICT (source_id) DO UPDATE SET
                        destination_ids = EXCLUDED.destination_ids,
                        profile_seed = EXCLUDED.profile_seed,
                        display_name = EXCLUDED.display_name,
                        avatar_url = EXCLUDED.avatar_url,
                        dicebear_failed = EXCLUDED.dicebear_failed,
                        image_filename = EXCLUDED.image_filename,
                        attachment_notes = EXCLUDED.attachment_notes,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        source_id,
                        normalized_destination_ids,
                        profile_seed,
                        display_name,
                        avatar_url,
                        dicebear_failed,
                        attachment_payload["image_filename"],
                        attachment_payload["notes"],
                    ),
                )

    def get(self, source_id: int) -> Optional[BridgeMessageRecord]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"SELECT * FROM {self._table_name} WHERE source_id = %s",
                    (source_id,),
                )
                record = cur.fetchone()
        if record is None:
            return None
        return BridgeMessageRecord.from_record(record)

    def update_metadata(
        self,
        *,
        source_id: int,
        attachments: Optional[BridgeMessageAttachmentMetadata] = None,
    ) -> None:
        record = self.get(source_id)
        if record is None:
            return

        image_filename = record.attachments.image_filename
        notes = list(record.attachments.notes)
        if attachments is not None:
            image_filename = attachments.image_filename
            notes = list(attachments.notes)

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET image_filename = %s,
                        attachment_notes = %s,
                        updated_at = clock_timestamp()
                    WHERE source_id = %s
                    """,
                    (image_filename, notes, source_id),
                )

    def delete(self, source_id: int) -> bool:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE source_id = %s",
                    (source_id,),
                )
                return cur.rowcount > 0

    def remove_destination(self, destination_id: int) -> None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT source_id, destination_ids
                    FROM {self._table_name}
                    WHERE destination_ids @> %s
                    LIMIT 1
                    """,
                    ([destination_id],),
                )
                record = cur.fetchone()

        if record is None:
            return

        remaining = [int(value) for value in record["destination_ids"] if int(value) != destination_id]
        if remaining:
            normalized = sorted(dict.fromkeys(remaining))
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE {self._table_name}
                        SET destination_ids = %s,
                            updated_at = clock_timestamp()
                        WHERE source_id = %s
                        """,
                        (normalized, record["source_id"]),
                    )
        else:
            self.delete(record["source_id"])

    def purge_older_than(self, *, threshold: datetime) -> int:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._table_name} WHERE updated_at < %s",
                    (threshold,),
                )
                return cur.rowcount


def _normalize_destination_ids(values: Iterable[int]) -> List[int]:
    normalized = sorted(dict.fromkeys(int(value) for value in values))
    return normalized


def _parse_datetime(value: Optional[datetime | str]) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


__all__ = [
    "BridgeMessageAttachmentMetadata",
    "BridgeMessageRecord",
    "BridgeMessageStore",
]
