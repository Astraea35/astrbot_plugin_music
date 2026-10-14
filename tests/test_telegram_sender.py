import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


package = ModuleType("telegram_music_test")
package.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[package.__name__] = package
MusicSender = importlib.import_module("telegram_music_test.core.sender").MusicSender


@pytest.mark.asyncio
async def test_telegram_selection_uses_text_even_when_qq_prefers_image():
    sender = MusicSender.__new__(MusicSender)
    sender.cfg = SimpleNamespace(real_select_modes=["image", "text"])
    sender._send_song_selection_text = AsyncMock()
    sender._send_song_selection_image = AsyncMock()
    event = SimpleNamespace(get_platform_name=lambda: "telegram")
    assert await sender.send_song_selection(event, [], None) == "text"
    sender._send_song_selection_text.assert_awaited_once()
    sender._send_song_selection_image.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["telegram", "aiocqhttp"])
async def test_lyrics_are_text_only_on_telegram(platform):
    sender = MusicSender.__new__(MusicSender)
    sender.lyrics_renderer = SimpleNamespace(draw_lyrics=Mock(return_value=b"image"))
    event = SimpleNamespace(
        get_platform_name=lambda: platform, send=AsyncMock(),
        plain_result=lambda text: text,
    )
    player = SimpleNamespace(resolve_lyrics=AsyncMock())
    song = SimpleNamespace(lyrics="line one\nline two", name="Test", artists="Artist")
    assert await sender.send_lyrics(event, player, song)
    if platform == "telegram":
        sender.lyrics_renderer.draw_lyrics.assert_not_called()
        assert "line one\nline two" in event.send.call_args.args[0]
    else:
        sender.lyrics_renderer.draw_lyrics.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["record", "file", "record_link", "file_link"])
async def test_telegram_media_uses_local_proxy_downloader(mode):
    sender = MusicSender.__new__(MusicSender)
    sender.cfg = SimpleNamespace(recall_select=False, enable_comments=False, enable_lyrics=False)
    sender._is_mode_supported = Mock(return_value=True)
    delivery = AsyncMock(return_value=True)
    sender._get_sender = Mock(return_value=delivery)
    sender.clear_selection_context = Mock()
    event = SimpleNamespace(
        get_platform_name=lambda: "telegram", get_sender_name=lambda: "Owner",
        get_sender_id=lambda: "123",
    )
    player = SimpleNamespace(platform=SimpleNamespace(display_name="Music"))
    song = SimpleNamespace(audio_url="audio", cover_url="cover", name="Test", artists="Artist")
    await sender.send_song(event, player, song, modes=[mode])
    sender._get_sender.assert_called_once_with(mode.removesuffix("_link") + "_local")
    delivery.assert_awaited_once()
