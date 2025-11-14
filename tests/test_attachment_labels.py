from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import discord

from bot.bridge.manager import ATTACHMENT_LABELS, ChannelBridgeManager


def _build_manager() -> ChannelBridgeManager:
    client = MagicMock(spec=discord.Client)
    profile_store = MagicMock()
    message_store = MagicMock()
    return ChannelBridgeManager(
        client=client,
        profile_store=profile_store,
        message_store=message_store,
        routes=[],
    )


def _attachment(filename: str, content_type: str | None) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, content_type=content_type)


def test_attachment_label_uses_filename_when_content_type_missing() -> None:
    manager = _build_manager()
    attachment = _attachment("photo.JPG", None)

    label = manager._attachment_label(attachment)

    assert label == ATTACHMENT_LABELS["image"]


def test_attachment_label_detects_audio_extension() -> None:
    manager = _build_manager()
    attachment = _attachment("voice_note.MP3", None)

    label = manager._attachment_label(attachment)

    assert label == ATTACHMENT_LABELS["audio"]


def test_attachment_label_falls_back_to_default_for_unknown_extension() -> None:
    manager = _build_manager()
    attachment = _attachment("archive.bin", None)

    label = manager._attachment_label(attachment)

    assert label == ATTACHMENT_LABELS["default"]
