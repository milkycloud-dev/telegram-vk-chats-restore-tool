<p align="center">
  <img src="logo.png" alt="Chat Restore Icon" width="300"/>
</p>

<h1 align="center">Replay — VK / Telegram → Telegram</h1>

<p align="center">
  <b>Recreates exported VK and Telegram conversations in a Telegram supergroup by replaying them through bots. Bridging memories across platforms.</b>
</p>

---

## 🇬🇧 English

Replay is a powerful tool designed to restore fragmented chat history from different social networks (VK and Telegram) into a single, unified Telegram timeline. By replaying them chronologically through designated bots, the two (or more) sides of the conversation are clearly preserved and distinguished.

### Features
- **Multi-task mode**: Configure and run multiple independent replay jobs from a single GUI.
- **VK + Telegram Replay**: Parses VkOpt JSON exports and Telegram Desktop HTML exports.
- **Smart Sender Detection**: Scans folders for unique sender IDs so you can map them to custom bots instantly.
- **Multi-chat Support**: Run all messages through one bot with a `[SenderName]` prefix if needed.
- **Resilient & Reliable**: Unstable-network resilient. Auto-handles 429 Flood Waits, infinite text retries, and bounded media retries. 
- **Rich User Interface**: Live progress bars, statistics, resource monitors, and dynamic bilingual support (switch languages on the fly).
- **Attachments Filter**: Filter photos, stickers, voice, audio, video, GIF, documents, and VK gifts (converted to stickers).

### Setup and Running
1. Clone the repository and install dependencies from `requirements.txt`.
2. Configure your bot tokens and target supergroups.
3. Launch `gui.py` or the compiled `.exe` artifact.
4. Add tasks and let the restore process begin!

---

## 🇷🇺 Русский

Replay — это мощный инструмент, предназначенный для восстановления фрагментированной истории чатов из разных социальных сетей (ВКонтакте и Telegram) в единую временную шкалу Telegram. Воспроизводя их в хронологическом порядке через назначенных ботов, стороны разговора (две или более) четко сохраняются и различаются.

### Особенности
- **Многозадачный режим**: Настраивайте и запускайте несколько независимых задач экспорта из одного интерфейса.
- **ВК + Telegram**: Парсит JSON-экспорты VkOpt и HTML-экспорты Telegram Desktop.
- **Умное обнаружение отправителей**: Сканирует папки на наличие уникальных ID отправителей, чтобы вы могли мгновенно привязать их к нужным ботам.
- **Мульти-чат**: Пропускайте все сообщения через одного бота с префиксом `[Имя отправителя]`.
- **Отказоустойчивость**: Устойчив к нестабильной сети. Автоматически обрабатывает 429 Flood Waits, бесконечно повторяет текст и ограничивает попытки медиа.
- **Богатый интерфейс**: Живые полосы прогресса, статистика, мониторинг ресурсов и динамическая поддержка двух языков (переключение на лету).
- **Фильтр вложений**: Выбирайте фото, стикеры, голос, аудио, видео, GIF, документы и подарки ВК (конвертируются в стикеры).

### Установка и запуск
1. Склонируйте репозиторий и установите зависимости из `requirements.txt`.
2. Настройте токены ботов и целевые супергруппы.
3. Запустите `gui.py` или скомпилированный `.exe` файл.
4. Добавьте задачи и начните процесс восстановления!
