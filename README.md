<p align="center">
  <img src="logo.png" alt="Chat Restore" width="700"/>
</p>

<h1 align="center">Replay — VK / Telegram → Telegram</h1>

<p align="center">
  Recreates exported VK and Telegram conversations in a Telegram supergroup by
  replaying them through bots. Each bot posts under its own name, so the two (or
  more) sides of the conversation are clearly distinguished.
</p>

Supports **multi-task mode** — restore multiple chats in one session, each with
its own target group, sources, bots and sender configuration.

## Features

- **VK + Telegram replay** — parse VkOpt JSON exports and Telegram Desktop HTML
  exports, then replay them chronologically in a Telegram supergroup.
- **Multi-task** — configure and run several independent replay jobs from one GUI.
- **Multi-chat** — optional single-bot mode where all messages go through one bot
  with a `[SenderName]` prefix (useful for group chats with many participants).
- **Auto-detect senders** — when you add a VK JSON or Telegram folder, the app
  scans for unique sender IDs / names so you can assign them to bots instantly.
- **Attachment type filter** — choose which attachment types to send (photos,
  stickers, voice, audio, video, GIF, documents, VK gifts).
- **Resumable** — progress is saved after every action; restart any time to
  continue where you left off.
- **Pausable / skippable / stoppable** — full control from the GUI.
- **Unstable-network resilient** — infinite retries for text messages, bounded
  retries for media, automatic 429 flood-wait handling. Nothing crashes and
  progress never moves backward.
- **Rich GUI** — live progress bars (overall + per-source), statistics,
  resource monitor, journal, error window with timestamps.
- **VK gifts as stickers** — gift images are converted to WebP and sent as
  Telegram stickers with a `🎁 [подарок]` label.
- **Media availability** — uses local HTTrack media mirrors for VK and local
  files from the Telegram export. Missing media falls back to labeled text
  placeholders.

## Supported Content

| Source   | Type                 | How it's sent                                       |
|----------|----------------------|-----------------------------------------------------|
| VK       | Photos               | Local file or URL → `sendPhoto`                     |
| VK       | Voice messages        | Local mp3 → auto-converted to ogg/opus → voice bubble |
| VK       | Audio tracks          | Local mp3 → `sendAudio`                             |
| VK       | Videos               | Title + `vk.com/video…` link (not downloaded)       |
| VK       | Stickers             | Downloaded from vk.com → WebP → `sendSticker`       |
| VK       | Gifts                | Gift image → WebP sticker + `🎁` label              |
| VK       | GIF / documents      | Local file → `sendAnimation` / `sendDocument`       |
| Telegram | Photos               | Local `photos/` → `sendPhoto`                       |
| Telegram | Static stickers      | Local `.webp` → `sendSticker`                       |
| Telegram | Animated stickers    | Local `.tgs` (Lottie) → `sendSticker`               |
| Telegram | Video stickers       | Local `.webm` → `sendSticker`                       |
| Telegram | Voice messages       | Local `.ogg` → `sendVoice`                          |
| Telegram | Videos / round notes | Local `.mp4` → `sendVideo` / `sendVideoNote`        |
| Telegram | Documents            | Local `files/` → `sendDocument`                     |
| Telegram | Calls                | Detailed text: direction, date, time range, duration |

Missing or expired media is replaced with a labeled text placeholder.

## Setup

```bash
pip install -r requirements.txt
python gui.py
```

**Python 3.11+** required.

### Requirements

- `requests` — HTTP client for Telegram Bot API and VK media downloads
- `Pillow` — image manipulation (sticker conversion, icon, verify samples)
- `imageio-ffmpeg` — bundled ffmpeg binary for voice/audio/video sample generation
- `psutil` — optional; shows RAM/CPU/thread count in the GUI

## Quick Start

1. **Create bots** — talk to [@BotFather](https://t.me/BotFather) on Telegram and
   create one bot per person in the conversation. Copy each token.
2. **Create a supergroup** — make a new Telegram supergroup and add all your bots
   as admins. Copy the group's Chat ID (starts with `-100…`).
3. **Export VK chat** — use the [VkOpt](https://vkopt.net/) browser extension to
   export messages as JSON.
4. **Export Telegram chat** — in Telegram Desktop, open the chat → ⋮ → Export →
   choose HTML format.
5. **Launch the GUI** — `python gui.py`. In the ⚙ Settings tab:
   - Set the **Chat ID** of your supergroup.
   - Add your **VK JSON** file(s) and/or **Telegram export** folder(s).
   - Add your **bots** (name + token). Assign VK sender IDs and TG display names
     to each bot.
   - Click **🔍 Обнаружить отправителей** to auto-scan sources for sender
     IDs/names.
   - Click **💾 Сохранить настройки**.
6. **Run** — switch to the ▶ Run tab, pick a task, click **▶ Старт**.

## Configuration (`settings.json`)

All settings live in `settings.json` (auto-created on first run). The GUI edits
this file; you can also open it in any text editor.

```jsonc
{
  "tasks": [
    {
      "name": "My Chat",
      "mode": "vk_and_tg",           // vk_only | tg_only | vk_and_tg
      "multichat": false,             // single-bot mode with [Name] prefix
      "target": { "chat_id": -100… },
      "sources": {
        "vk_exports": [
          { "path": "C:\\path\\to\\vk_messages.json", "label": "VK" }
        ],
        "telegram_exports": [
          { "path": "C:\\path\\to\\telegram_chat", "label": "Telegram" }
        ],
        "vk_media_mirrors": [
          { "cache": "…/hts-cache/new.txt", "web": "…/web" }
        ]
      },
      "bots": {
        "alice": "123456:AAH…token…",
        "bob":   "789012:AAE…token…"
      },
      "sender_map": {
        "vk": { "12345678": "alice", "87654321": "bob" },
        "vk_default": "bob",
        "telegram": { "alice name": "alice", "bob name": "bob" },
        "telegram_default": "bob"
      },
      "display_names": { "alice": "Alice", "bob": "Bob" },
      "system_bot": "bob",
      "attachments_filter": {
        "photo": true, "sticker": true, "voice": true,
        "audio": true, "video": true, "video_note": true,
        "animation": true, "document": true, "gift": true
      },
      "rate": { "min_interval_seconds": 1.5 },
      "retry": { "send_media_attempts": 6 },
      "behavior": {
        "send_date_headers": true,
        "send_section_headers": true,
        "placeholders_for_missing": true
      }
    }
  ]
}
```

## Multi-Task Mode

Add multiple tasks — each is an independent replay job with its own target chat,
sources, bots, and sender mapping. In the GUI, use **+ Добавить задачу** to create
new tasks and pick which one to run from the dropdown in the ▶ Run tab.

## Multi-Chat Mode

Enable the **Мульти-чат** checkbox for group chats with many participants. In this
mode, a single bot sends all messages, prefixing each with `[SenderName]` so you
can tell who said what.

## CLI Usage

```bash
# Run task 0 (default)
python run_export.py

# Run task 1
python run_export.py --task 1

# Parse and count only (no sends)
python run_export.py --dry-run

# Reset progress and start over
python run_export.py --reset

# Send at most 100 messages
python run_export.py --limit 100
```

## Verification

```bash
python verify.py
```

Sends one of every attachment type to the target chat so you can verify rendering
before the full replay: text, sticker, photo, GIF, voice, audio, video, round
video note, document, and a placeholder example.

## Ledger — What Was Sent

Every action is recorded:

- `results.jsonl` — one JSON line per action (index, source, sender, status,
  attachment details).
- `not_sent.log` — human-readable list of items that were not sent as real media
  (placeholder / skipped / error), with date and text preview.

## Files

| File                 | Purpose                                                    |
|----------------------|------------------------------------------------------------|
| `gui.py`             | Desktop GUI: tasks, progress, stats, start/pause/skip/stop |
| `run_export.py`      | CLI orchestrator with resume support                       |
| `settings_manager.py`| Load / save / validate `settings.json`                     |
| `config.py`          | Runtime configuration (patched from settings)              |
| `models.py`          | Normalized `Event` / `Attachment` data types               |
| `vk_parser.py`       | Parse VkOpt JSON → events                                  |
| `tg_parser.py`       | Parse Telegram HTML export → events                        |
| `telegram_client.py` | Bot API wrapper: pacing, 429/5xx retries, all send methods |
| `sender.py`          | Event → real sends with media fallbacks                    |
| `media.py`           | Download, sticker/voice conversion, caching                |
| `media_map.py`       | Maps VK media URLs → local HTTrack files                   |
| `control.py`         | Shared pause/stop/skip + thread-safe live statistics       |
| `verify.py`          | Pre-flight test of every attachment type                   |
| `settings.json`      | User settings (auto-managed)                               |
| `state.json`         | Resume progress (auto-managed)                             |
| `results.jsonl`      | Full per-item ledger of outcomes                           |
| `not_sent.log`       | Items not fully sent as real media                         |
| `cache/`             | Downloaded media + generated samples (safe to delete)      |

## License

**All Rights Reserved** — see [LICENSE](LICENSE).

This software is proprietary. You may view the source code for personal study,
but you may not copy, distribute, modify, or use it commercially without
written permission from the author. See [LICENSE](LICENSE) for full terms.
