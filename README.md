<p align="center"><img src="logo.png" width="160" alt="Replay logo"></p>

<h1 align="center">Replay: VK and Telegram Chat Restore Tool</h1>

<p align="center">Desktop and CLI tool that replays exported VK and Telegram chats into one Telegram supergroup in the original order, with one bot per participant so every message keeps its sender. Resume, rate-limit handling, media placeholders.</p>

<p align="center"><a href="https://github.com/milkycloud-dev/telegram-vk-chats-restore-tool/actions/workflows/release.yml"><img src="https://github.com/milkycloud-dev/telegram-vk-chats-restore-tool/actions/workflows/release.yml/badge.svg" alt="Release"></a></p>

<p align="center"><a href="#english">English</a> | <a href="#русский">Русский</a></p>

<a id="english"></a>

## English

### Purpose

A conversation that moved from VK to Telegram, or lives in several exports, ends up split across files that nobody can read together. Replay parses the exports, merges them by time and posts the result into a Telegram supergroup, so the history reads as one chat again.

### Features

- **Sources.** VK JSON exports made with the VkOpt extension, including nested forwards; Telegram Desktop HTML exports with replies, media paths and stickers.
- **Senders.** Each original participant is posted by their own bot. The tool scans the exports, finds the senders and proposes a sender-to-bot map. With fewer bots, one bot can post everything with a `[Name]` prefix.
- **Tasks.** Several independent replays in one `settings.json`; the GUI edits them and shows each run.
- **Media.** Photos, stickers, voice, audio, video, video notes, GIF, documents and VK gifts. A missing or broken file becomes a labeled text placeholder.
- **Reliability.** `429` answers are handled with exponential backoff; text is retried until sent, media a limited number of times; progress is saved in `state.json`, so a stopped run continues.
- **Interface.** Tkinter GUI with progress, ETA, errors and thread and resource stats, in English and Russian; work runs in background threads.
- **Pre-flight check.** `verify.py` sends one sample of each attachment type to the target chat before the full run, with synthesized samples for types whose originals are gone.

### Setup

1. Python 3.14 or newer: `pip install -r requirements.txt`.
2. Create the bots with @BotFather and add all of them to the target supergroup as administrators.
3. Start `python gui.py`, add a task, paste the bot tokens, point it at the export folders and start.

CLI: `python run_export.py [--task N] [--dry-run] [--limit N] [--reset]`. `--dry-run` only parses and counts.

`settings.json` holds bot tokens once filled in; do not share or commit it.

### Releases

A tag `v*` builds `ChatRestoreTool_Windows.zip` and `ChatRestoreTool_Linux.tar.gz` with PyInstaller on GitHub Actions and publishes them with the notes from [CHANGELOG.md](CHANGELOG.md).

### License

Proprietary, all rights reserved. Running the official release builds is allowed; see [LICENSE](LICENSE) for the full terms.

<a id="русский"></a>

## Русский

### Назначение

Переписка, которая переехала из VK в Telegram или лежит в нескольких выгрузках, оказывается разбросана по файлам, которые вместе не прочитать. Replay разбирает выгрузки, сводит их по времени и публикует результат в супергруппу Telegram, чтобы история снова читалась как один чат.

### Возможности

- **Источники.** JSON-выгрузки VK из расширения VkOpt, включая вложенные пересылки; HTML-выгрузки Telegram Desktop с ответами, путями к медиа и стикерами.
- **Отправители.** Каждого участника публикует свой бот. Инструмент сканирует выгрузки, находит отправителей и предлагает карту «отправитель: бот». Если ботов мало, один бот может публиковать всё с префиксом `[Имя]`.
- **Задачи.** Несколько независимых прогонов в одном `settings.json`; GUI их редактирует и показывает каждый запуск.
- **Медиа.** Фото, стикеры, голосовые, аудио, видео, кружки, GIF, документы и подарки VK. Отсутствующий или битый файл заменяется подписанной текстовой заглушкой.
- **Надёжность.** Ответы `429` обрабатываются с экспоненциальной паузой; текст повторяется до отправки, медиа ограниченное число раз; прогресс хранится в `state.json`, остановленный прогон продолжается.
- **Интерфейс.** GUI на Tkinter с прогрессом, оставшимся временем, ошибками и статистикой потоков и ресурсов, на английском и русском; работа идёт в фоновых потоках.
- **Предпроверка.** `verify.py` отправляет в целевой чат по одному образцу каждого типа вложений до полного прогона, для типов без оригиналов собирает образцы сам.

### Настройка

1. Python 3.14 или новее: `pip install -r requirements.txt`.
2. Создайте ботов через @BotFather и добавьте их всех в целевую супергруппу администраторами.
3. Запустите `python gui.py`, добавьте задачу, вставьте токены ботов, укажите папки выгрузок и запустите.

CLI: `python run_export.py [--task N] [--dry-run] [--limit N] [--reset]`. `--dry-run` только разбирает и считает.

После заполнения в `settings.json` лежат токены ботов; его нельзя передавать и коммитить.

### Релизы

Тег `v*` собирает `ChatRestoreTool_Windows.zip` и `ChatRestoreTool_Linux.tar.gz` через PyInstaller в GitHub Actions и публикует их с описанием из [CHANGELOG.md](CHANGELOG.md).

### Лицензия

Проприетарная, все права защищены. Запуск официальных сборок из релизов разрешён; полные условия в [LICENSE](LICENSE).
