from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from supabase import Client


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

    def __init__(self, supabase: Client, table_name: str = "bridge_messages") -> None:
        self._supabase = supabase
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
        payload = {
            "source_id": source_id,
            "destination_ids": normalized_destination_ids,
            "profile_seed": profile_seed,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "dicebear_failed": dicebear_failed,
            "image_filename": attachment_payload["image_filename"],
            "attachment_notes": list(attachment_payload["notes"]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._supabase.table(self._table_name).upsert(
            payload,
            on_conflict="source_id",
        ).execute()

    def get(self, source_id: int) -> Optional[BridgeMessageRecord]:
        response = (
            self._supabase.table(self._table_name)
            .select("*")
            .eq("source_id", source_id)
            .execute()
        )
        if isinstance(response.data, list) and response.data:
            return BridgeMessageRecord.from_record(response.data[0])
        if isinstance(response.data, dict):
            return BridgeMessageRecord.from_record(response.data)
        return None

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

        self._supabase.table(self._table_name).update(
            {
                "image_filename": image_filename,
                "attachment_notes": notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("source_id", source_id).execute()

    def delete(self, source_id: int) -> bool:
        response = (
            self._supabase.table(self._table_name)
            .delete()
            .eq("source_id", source_id)
            .execute()
        )
        if isinstance(response.data, list):
            return len(response.data) > 0
        return bool(response.data)

    def remove_destination(self, destination_id: int) -> None:
        response = (
            self._supabase.table(self._table_name)
            .select("source_id, destination_ids")
            .contains("destination_ids", [destination_id])
            .limit(1)
            .execute()
        )
        record = None
        if isinstance(response.data, list) and response.data:
            record = response.data[0]
        elif isinstance(response.data, dict):
            record = response.data

        if record is None:
            return

        remaining = [int(value) for value in record.get("destination_ids", []) if int(value) != destination_id]
        if remaining:
            normalized = sorted(dict.fromkeys(remaining))
            self._supabase.table(self._table_name).update(
                {
                    "destination_ids": normalized,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("source_id", record["source_id"]).execute()
        else:
            self.delete(int(record["source_id"]))

    def purge_older_than(self, *, threshold: datetime) -> int:
        response = (
            self._supabase.table(self._table_name)
            .delete()
            .lt("updated_at", threshold.isoformat())
            .execute()
        )
        if isinstance(response.data, list):
            return len(response.data)
        return 0


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
