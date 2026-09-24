<p align="center">
  <img src="logo.png" alt="Replay Logo" width="300"/>
</p>

<h1 align="center">Replay: VK / Telegram to Telegram Restore Tool</h1>

<p align="center">
  <b>A powerful, asynchronous restoration engine that reconstructs exported VKontakte and Telegram chats into a unified Telegram supergroup timeline, intelligently preserving the original multi-user flow.</b>
</p>

---

## English

Replay is an advanced CLI/GUI application designed to chronologically stitch and replay fragmented chat histories from different social networks (VK and Telegram) into a single Telegram environment. By simulating multiple participants through individual Telegram bots, Replay ensures that complex conversations spanning years and platforms are preserved with perfect context, sender identity, and precise chronological ordering.

### Core Capabilities & Technical Features
- **Multi-task Concurrency**: Configure and execute multiple independent replay operations from a single JSON-based settings schema. The Tkinter UI builds the configuration and monitors the running processes.
- **Dual Source Parsers**: 
  - **VKontakte**: Parses legacy JSON exports from the popular `VkOpt` extension. Recreates nested message hierarchies, forwarded structures, and decodes legacy VK payload mappings.
  - **Telegram**: Parses standard Telegram Desktop HTML exports. Ingests all internal DOM structures to map media paths, nested replies, and sticker payloads correctly.
- **Smart Sender Inference**: Implements a fuzzy-matching scan mechanism over source directories to detect unique sender IDs and metadata. Automatically creates a sender-to-bot mapping configuration block for immediate use.
- **Multi-chat Routing**: Allows fallback to a single-bot `[Sender Name]` prefix mode to conserve Telegram bots while maintaining readability across massive groups.
- **Network Resilience & Backoff Policy**: Built for stability against rate-limits. Dynamically handles Telegram's `429 Flood Wait` exceptions using exponential backoff, guarantees infinite text transmission retries, and enforces bounded (configurable) media upload retries to avoid deadlocks.
- **Diagnostic UI**: work runs in background threads, so the UI does not freeze. Live progress bars, detailed error logs, resource/thread monitoring, ETA, and switching between two languages on the fly.
- **Media Transcoding & Placeholders**: Filters through 9+ types of media (Photos, Stickers, Voice, Audio, Video, Video Notes, GIF, Documents, VK Gifts). Automatically injects descriptive `[Media Placeholder]` text when the original file is missing, corrupted, or unreachable.

### Installation & Deployment
1. Ensure Python 3.14+ is installed.
2. Clone the repository and install dependencies: `pip install -r requirements.txt`.
3. Register your bots via `@BotFather` and retrieve API tokens.
4. Add all required bots as Administrators to your target Telegram Supergroup.
5. Launch `gui.py` (or execute the bundled `Chat Restore Tool.exe`).
6. Add tasks via the interface, map your bot tokens, link your raw export directories, and start the replay pipeline.

---

## Русский

Replay собирает историю чатов из ВКонтакте и Telegram в одну хронологическую ленту Telegram-супергруппы. Каждого участника изображает отдельный Telegram-бот, поэтому у сообщений сохраняются имена отправителей, контекст и порядок, даже если переписка шла годами.

### Ключевые возможности и технические детали
- **Многозадачная архитектура**: Настраивайте и запускайте несколько независимых процессов восстановления на основе единой схемы `settings.json`. Интерфейс на Tkinter выступает надежным генератором конфигураций и монитором процессов.
- **Два встроенных парсера**: 
  - **ВКонтакте**: Обрабатывает JSON-дампы от расширения `VkOpt`. Восстанавливает вложенные сообщения, пересылки и декодирует старые форматы VK.
  - **Telegram**: Парсит HTML-дампы Telegram Desktop. Извлекает внутреннюю структуру DOM для точной привязки путей к медиафайлам, ответам и стикерам.
- **Сканирование отправителей**: нечёткий поиск по папкам с исходниками находит ID отправителей, собирает их метаданные и сам генерирует блок конфигурации для привязки ботов.
- **Режим мульти-чата**: Резервный режим маршрутизации всех сообщений через одного бота с префиксом `[Имя Отправителя]` для экономии лимитов Telegram-ботов при восстановлении крупных групп.
- **Устойчивость к лимитам**: Защита от банов и rate-limit блокировок. Динамически обрабатывает исключения `429 Flood Wait` через экспоненциальную задержку. Гарантирует бесконечные попытки отправки текста и ограниченные (настраиваемые) попытки загрузки медиа во избежание зависаний.
- **Аналитический UI**: Использует нативную многопоточность для предотвращения зависаний интерфейса. Содержит живые прогресс-бары, подробные логи ошибок, монитор потоков, расчет времени (ETA) и мгновенное переключение языка.
- **Транскодирование медиа и заглушки**: Фильтрация более 9 типов вложений (Фото, Стикеры, Голосовые, Аудио, Видео, Кружочки, GIF, Документы, Подарки ВК). Если оригинальный файл утерян или поврежден, инструмент автоматически инжектирует текстовую `[Заглушку]` в историю.

### Установка и настройка
1. Убедитесь, что установлен Python 3.14+.
2. Склонируйте репозиторий и установите пакеты: `pip install -r requirements.txt`.
3. Зарегистрируйте необходимое количество ботов через `@BotFather` и получите токены API.
4. Добавьте всех ботов в качестве Администраторов в целевую супергруппу Telegram.
5. Запустите `gui.py` (или готовый билд `Chat Restore Tool.exe`).
6. Через графический интерфейс настройте задачи, привяжите токены, укажите пути к папкам экспорта и запустите процесс.
