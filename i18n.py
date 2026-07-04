"""Internationalization (i18n) module for the chat replay tool.

Supports Russian (ru) and English (en) with a global language switch.
All user-facing strings are accessed via ``t(key)`` or ``t(key, **kwargs)``
for parameterized messages.

Usage::

    from i18n import t, set_lang, get_lang
    set_lang("en")
    print(t("gui.btn_start"))   # "▶ Start"
"""
from __future__ import annotations

_LANG = "ru"

# ---------------------------------------------------------------------------
#  Russian strings (default)
# ---------------------------------------------------------------------------
_RU: dict[str, str] = {
    # ── gui.py — time formatting ──────────────────────────────────────────
    "time.h": "ч",
    "time.m": "м",
    "time.s": "с",

    # ── gui.py — window ───────────────────────────────────────────────────
    "gui.window_title": "Replay — VK / Telegram → Telegram",

    # ── gui.py — tabs ─────────────────────────────────────────────────────
    "gui.tab_run": "  ▶ Запуск  ",
    "gui.tab_settings": "  ⚙ Настройки  ",

    # ── gui.py — run tab — task selector ──────────────────────────────────
    "gui.task_label": "Задача:",
    "gui.task_n": "Задача {n}",

    # ── gui.py — run tab — control buttons ────────────────────────────────
    "gui.btn_start": "▶ Старт",
    "gui.btn_pause": "⏸ Пауза",
    "gui.btn_resume": "▶ Продолжить",
    "gui.btn_skip": "⏭ Пропустить",
    "gui.btn_stop": "⏹ Стоп",
    "gui.btn_test": "🧪 Тест",
    "gui.btn_errors": "🚨 Ошибки",
    "gui.btn_log": "📄 Лог",
    "gui.reset_progress": "Начать заново",

    # ── gui.py — run tab — progress ───────────────────────────────────────
    "gui.progress_frame": "Прогресс",
    "gui.phase": "Фаза: {v}",
    "gui.elapsed": "Прошло: {v}",
    "gui.remaining": "Осталось: {v}",
    "gui.speed": "Скорость: {v}/мин",
    "gui.current": "Текущее: {v}",
    "gui.file": "Файл: {v}  ({k})",
    "gui.vk_label": "ВК:",
    "gui.tg_label": "ТГ:",

    # ── gui.py — run tab — statistics ─────────────────────────────────────
    "gui.stats_frame": "Статистика",
    "gui.stat_text": "Текст",
    "gui.stat_photo": "Фото",
    "gui.stat_sticker": "Стикеры",
    "gui.stat_voice": "Голос",
    "gui.stat_video": "Видео",
    "gui.stat_document": "Файлы",
    "gui.stat_header": "Заголовки",
    "gui.stat_placeholder": "Заглушки",
    "gui.stat_skipped": "Пропуск",
    "gui.stat_errors": "Ошибки",
    "gui.stat_retries": "Повторы",

    # ── gui.py — run tab — resources ──────────────────────────────────────
    "gui.res_frame": "Ресурсы",
    "gui.res_ram": "RAM",
    "gui.res_cpu": "CPU",
    "gui.res_threads": "Потоки",
    "gui.res_downloads": "Загрузок",
    "gui.res_flood": "429",
    "gui.ram_mb": "{v} МБ",

    # ── gui.py — run tab — log ────────────────────────────────────────────
    "gui.log_frame": "Журнал",

    # ── gui.py — settings tab ─────────────────────────────────────────────
    "gui.btn_add_task": "+ Добавить задачу",
    "gui.btn_save_settings": "💾 Сохранить настройки",
    "gui.btn_reload": "↻ Перезагрузить из файла",
    "gui.btn_open_settings": "📂 Открыть settings.json",
    "gui.btn_validate": "🔍 Проверить пути",

    # ── gui.py — task panel ───────────────────────────────────────────────
    "gui.task_name_label": "Название:",
    "gui.btn_delete_task": "✕ Удалить задачу",
    "gui.target_frame": "Целевой чат Telegram",
    "gui.chat_id_hint": "(для супергруппы: -100…)",
    "gui.mode_frame": "Режим отправки",
    "gui.multichat_label": "Мульти-чат (один бот, [Имя] перед сообщением)",
    "gui.vk_frame": "ВКонтакте — JSON экспорт (+)",
    "gui.btn_add_vk": "+ Добавить VK JSON",
    "gui.tg_frame": "Telegram — папки экспорта (+)",
    "gui.btn_add_tg": "+ Добавить папку TG",
    "gui.bots_frame": "Боты и отправители",
    "gui.btn_add_bot": "+ Добавить бота",
    "gui.btn_detect": "🔍 Обнаружить отправителей",
    "gui.att_frame": "Вложения (что отправлять)",
    "gui.rate_frame": "Скорость и поведение",
    "gui.delay_label": "Пауза, с:",
    "gui.attempts_label": "Попыток медиа:",
    "gui.date_headers": "Заголовки дат",
    "gui.section_headers": "Заголовки секций",
    "gui.placeholders_missing": "Заглушки для отсутствующих файлов",

    # ── gui.py — VkExportRow / TgExportRow / BotRow ───────────────────────
    "gui.row_json": "JSON:",
    "gui.row_folder": "Папка:",
    "gui.row_title": "Заголовок:",
    "gui.row_bot_name": "Имя:",
    "gui.row_bot_token": "Токен:",
    "gui.row_bot_system": "Сист.",
    "gui.row_bot_default": "По ум.",
    "gui.row_bot_display": "Отобр.:",
    "gui.row_bot_tg_names": "TG имена:",

    # ── gui.py — default labels ───────────────────────────────────────────
    "gui.vk_default_label": "ВК",
    "gui.vk_default_label_n": "ВК {n}",
    "gui.tg_default_label": "Телеграм",
    "gui.tg_default_label_n": "Телеграм {n}",

    # ── gui.py — detect senders ───────────────────────────────────────────
    "gui.detected_vk": "VK отправители: {v}",
    "gui.detected_tg": "TG отправители: {v}",

    # ── gui.py — dialogs / messages ───────────────────────────────────────
    "gui.cannot_delete_last": "Нельзя удалить единственную задачу.",
    "gui.dlg_tasks_title": "Задачи",
    "gui.settings_loaded": "Настройки загружены из settings.json",
    "gui.load_error_title": "Ошибка",
    "gui.load_error_msg": "Не удалось загрузить settings.json:\n{e}",
    "gui.save_warning_title": "Проверка",
    "gui.save_warning_msg": "Сохранено, но есть замечания:\n\n{errs}",
    "gui.saved_log": "Настройки сохранены: {path}",
    "gui.saved_title": "Сохранено",
    "gui.saved_msg": "Настройки записаны в\n{path}",
    "gui.error_title": "Ошибка",
    "gui.msg_error_title": "Ошибка",
    "gui.msg_settings_load_err": "Не удалось загрузить settings.json:\n{err}",
    "gui.validate_ok_title": "Проверка",
    "gui.validate_ok_msg": "Все пути и параметры в порядке ✓",
    "gui.validate_warn_title": "Проверка",
    "gui.no_task_selected": "Не выбрана задача.",
    "gui.start_warning_title": "Предупреждение",
    "gui.start_warning_msg": "Есть проблемы с настройками:\n\n{errs}\n\nВсё равно запустить?",
    "gui.run_log_start": "=== Запуск: {name} ===",
    "gui.critical_error": "!!! Критическая ошибка: {e}",
    "gui.paused_log": "Пауза.",
    "gui.resumed_log": "Продолжено.",
    "gui.skip_requested_log": "Запрошен пропуск…",
    "gui.stop_title": "Стоп",
    "gui.stop_msg": "Остановить? Прогресс сохранится.",
    "gui.stopping_log": "Остановка…",
    "gui.test_log": "=== Тест вложений ===",
    "gui.log_title": "Лог",
    "gui.file_title": "Файл",

    # ── gui.py — error window ─────────────────────────────────────────────
    "gui.err_window_title": "Ошибки и события",
    "gui.err_clear": "Очистить",
    "gui.err_col_time": "Время",
    "gui.err_col_type": "Тип",
    "gui.err_col_msg": "Сообщение",
    "gui.err_count": "Событий: {n}",

    # ── gui.py — language switcher ────────────────────────────────────────
    "gui.lang_label": "Язык:",

    # ── settings_manager.py — mode labels ─────────────────────────────────
    "mode.vk_only": "Только ВКонтакте",
    "mode.tg_only": "Только Telegram",
    "mode.vk_and_tg": "ВК + Telegram",

    # ── settings_manager.py — attachment labels ───────────────────────────
    "att.photo": "Фото",
    "att.sticker": "Стикеры",
    "att.voice": "Голосовые",
    "att.audio": "Аудио",
    "att.video": "Видео",
    "att.video_note": "Видеосообщения",
    "att.animation": "GIF",
    "att.document": "Документы",
    "att.gift": "Подарки (ВК)",

    # ── settings_manager.py — default names ───────────────────────────────
    "settings.default_task_name": "Задача 1",
    "settings.default_task": "Задача",
    "settings.default_vk_label": "ВК",
    "settings.default_vk_label_n": "ВК {n}",
    "settings.default_tg_label": "Телеграм {n}",

    # ── settings_manager.py — validation errors ──────────────────────────
    "val.no_chat_id": "Не указан Chat ID целевого чата.",
    "val.no_vk_export": "Не добавлен ни один VK JSON экспорт.",
    "val.vk_not_found": "VK JSON не найден: {path}",
    "val.no_tg_export": "Добавьте хотя бы одну папку экспорта Telegram.",
    "val.tg_dir_not_found": "Папка Telegram не найдена: {path}",
    "val.tg_no_messages": "В папке нет messages*.html: {path}",
    "val.no_bots": "Не добавлен ни один бот.",
    "val.no_token": "Не указан токен для бота «{key}».",
    "val.multichat_bot_missing": "Бот мульти-чата «{bot}» не найден в списке ботов.",
    "val.delay_not_number": "Пауза между сообщениями должна быть числом.",

    # ── settings_manager.py — summaries ───────────────────────────────────
    "summary.mode": "Режим: {mode}",
    "summary.chat": "Chat: {chat}",
    "summary.vk_count": "ВК: {n}",
    "summary.tg_count": "ТГ: {n}",
    "summary.bots_count": "Ботов: {n}",
    "summary.multichat": "мульти-чат",
    "summary.tasks_count": "Задач: {n}",

    # ── run_export.py — date formatting ───────────────────────────────────
    "date.january": "января",
    "date.february": "февраля",
    "date.march": "марта",
    "date.april": "апреля",
    "date.may": "мая",
    "date.june": "июня",
    "date.july": "июля",
    "date.august": "августа",
    "date.september": "сентября",
    "date.october": "октября",
    "date.november": "ноября",
    "date.december": "декабря",
    "date.format": "{day} {month} {year}",

    # ── run_export.py — preview / phases ──────────────────────────────────
    "run.section_prefix": "── секция {label} ──",
    "run.phase_vk": "ВКонтакте",
    "run.phase_tg": "Телеграм",
    "run.empty": "(пусто)",
    "run.done": "Готово",

    # ── telegram_client.py — event log tags ───────────────────────────────
    "tag.no_network": "НЕТ СЕТИ",
    "tag.network": "СЕТЬ",
    "tag.server": "СЕРВЕР",
    "tag.error": "ОШИБКА",
    "tag.gave_up": "ОТКАЗ",
    "tag.flood": "429",

    # ── telegram_client.py — event log messages ───────────────────────────
    "net.no_connection": "{method}: нет соединения, ждём сеть ({err})",
    "net.attempt": "{method}: {err}: {msg} (попытка {n})",
    "net.gave_up_net": "{method}: пропуск вложения после {n} неудачных попыток",
    "net.flood_wait": "{method}: флуд-контроль, ожидание {sec}s",
    "net.server_error": "{method}: HTTP {code} (попытка {n})",
    "net.gave_up_server": "{method}: пропуск вложения после {n} попыток (сервер)",

    # ── media.py — event log ──────────────────────────────────────────────
    "tag.link": "ССЫЛКА",
    "tag.download": "ЗАГРУЗКА",
    "media.external_link": "внешняя ссылка не скачивается: {url}",
    "media.gone": "ВК-медиа недоступно (HTTP {code})",
    "media.download_retry": "загрузка: HTTP {code} (попытка {attempt}/{total})",
    "media.download_failed_http": "ВК-медиа: HTTP {code} после {total} попыток",
    "media.download_failed_err": "загрузка не удалась [{err}] (попытка {attempt}/{total})",
    "media.download_gave_up": "ВК-медиа не скачано [{err}] после {total} попыток",

    # ── vk_parser.py — placeholder notes ──────────────────────────────────
    "vk.photo_unavailable": "[фото недоступно]",
    "vk.photo": "[фото]",
    "vk.sticker": "[стикер]",
    "vk.graffiti": "[граффити]",
    "vk.voice_msg": "[голосовое сообщение, {dur}с]",
    "vk.gif": "[GIF]",
    "vk.image": "[изображение]",
    "vk.file": "[файл: {name}]",
    "vk.video_title": "видео",
    "vk.wall_repost": "[репост со стены]",
    "vk.wall_comment": "[комментарий со стены]",
    "vk.market_item": "[товар: {title}]",
    "vk.poll": "[опрос: {question}]",
    "vk.gift": "🎁 [подарок]",
    "vk.call": "[звонок]",
    "vk.story": "[история]",
    "vk.geo": "[геолокация]",
    "vk.attachment": "[вложение: {type}]",
    "vk.attachment_short": "вложение",
    "vk.reply_to": "↪ в ответ на: «{quote}»",
    "vk.forwarded": "[переслано]",

    # ── tg_parser.py — placeholder notes ──────────────────────────────────
    "tg.photo": "[фото]",
    "tg.sticker": "[стикер]",
    "tg.voice_msg": "[голосовое сообщение{dur}]",
    "tg.video_note": "[видеосообщение]",
    "tg.video": "[видео]",
    "tg.file": "[файл: {name}]",
    "tg.reply": "↪ в ответ",
    "tg.forwarded": "[переслано{src}]",

    # ── tg_parser.py — call formatting ────────────────────────────────────
    "call.h": "ч",
    "call.min": "мин",
    "call.sec": "сек",
    "call.missed": "📞 Пропущенный звонок",
    "call.cancelled": "📞 Отменённый звонок",
    "call.declined": "📞 Отклонённый звонок",
    "call.call": "📞 Звонок",
    "call.unanswered": "📞 Звонок (не отвечен)",
    "call.outgoing": "исходящий",
    "call.incoming": "входящий",
    "call.duration": "⏱ Длительность: {dur}",

    # ── sender.py ─────────────────────────────────────────────────────────
    "sender.gift_label": "🎁 [подарок]",

    # ── verify.py ─────────────────────────────────────────────────────────
    "verify.start_msg": "🔧 ПРОВЕРКА ВЛОЖЕНИЙ — начинаю отправку всех типов.",
    "verify.text_bot1": "Текст от бота 1 ✅",
    "verify.text_bot2": "Текст от бота 2 ✅",
    "verify.sticker_fallback": "стикер (как фото, fallback)",
    "verify.real_vk_photo": "реальное фото из ВК",
    "verify.test_photo": "тестовое фото",
    "verify.gif_animation": "GIF/анимация",
    "verify.voice_msg": "голосовое сообщение",
    "verify.audio_track": "аудио-трек",
    "verify.video": "видео",
    "verify.document": "документ",
    "verify.real_vk_voice": "реальное голосовое из ВК",
    "verify.real_vk_audio": "реальное аудио из ВК",
    "verify.placeholder_example": "[голосовое сообщение, 15с]\n(оригинал недоступен — ссылка истекла)",
    "verify.done_msg": "🔧 ПРОВЕРКА ЗАВЕРШЕНА.",
    "gui.title_label": "Заголовок:",
    "gui.folder_label": "Папка:",
    "gui.name_label": "Имя:",
    "gui.token_label": "Токен:",
    "gui.system_bot_flag": "Сист.",
    "gui.default_bot_flag": "По ум.",
    "gui.display_name_label": "Отобр.:",
    "gui.tg_names_label": "TG имена:",
    "gui.task_default_name": "Задача {num}",
    "gui.delete_task_btn": "✕ Удалить задачу",
    "gui.target_chat_frame": "Целевой чат Telegram",
    "gui.supergroup_hint": "(для супергруппы: -100…)",
    "gui.multichat_cb": "Мульти-чат (один бот, [Имя] перед сообщением)",
    "gui.add_vk_btn": "+ Добавить VK JSON",
    "gui.add_tg_btn": "+ Добавить папку TG",
    "gui.add_bot_btn": "+ Добавить бота",
    "gui.detect_senders_btn": "🔍 Обнаружить отправителей",
    "gui.attachments_frame": "Вложения (что отправлять)",
    "gui.behavior_frame": "Скорость и поведение",
    "gui.retries_label": "Попыток медиа:",
    "gui.date_hdr_cb": "Заголовки дат",
    "gui.sect_hdr_cb": "Заголовки секций",
    "gui.placeholders_cb": "Заглушки для отсутствующих файлов",
    "gui.vk_senders_found": "VK отправители: {senders}",
    "gui.tg_senders_found": "TG отправители: {senders}",
    "gui.btn_reset": "Начать заново",
    "gui.frame_progress": "Прогресс",
    "gui.lbl_phase": "Фаза:",
    "gui.lbl_elapsed": "Прошло:",
    "gui.lbl_eta": "Осталось:",
    "gui.lbl_rate": "Скорость:",
    "gui.lbl_current": "Текущее:",
    "gui.lbl_file": "Файл:",
    "gui.lbl_vk": "ВК:",
    "gui.lbl_tg": "ТГ:",
    "gui.rate_fmt": "Скорость: {rate:.0f}/мин",
    "gui.frame_stats": "Статистика",
    "gui.stat_placeholders": "Заглушки",
    "gui.frame_resources": "Ресурсы",
    "gui.frame_log": "Журнал",
    "gui.add_task_btn": "+ Добавить задачу",
    "gui.save_settings_btn": "💾 Сохранить настройки",
    "gui.reload_settings_btn": "↻ Перезагрузить из файла",
    "gui.open_settings_btn": "📂 Открыть settings.json",
    "gui.validate_paths_btn": "🔍 Проверить пути",
    "gui.msg_tasks_title": "Задачи",
    "gui.msg_cannot_delete_last": "Нельзя удалить единственную задачу.",
    "gui.msg_check_title": "Проверка",
    "gui.msg_saved_warnings": "Сохранено, но есть замечания:",
    "gui.msg_settings_saved_log": "Настройки сохранены: {path}",
    "gui.msg_settings_saved": "Настройки записаны в\n{path}",
    "gui.msg_check_ok": "Все пути и параметры в порядке ✓",
    "gui.msg_file_title": "Файл",
    "gui.msg_no_task_selected": "Не выбрана задача.",
    "gui.msg_warn_title": "Предупреждение",
    "gui.msg_settings_issues": "Есть проблемы с настройками:",
    "gui.msg_run_anyway": "Всё равно запустить?",
    "gui.log_start": "=== Запуск: {name} ===",
    "gui.log_critical_err": "!!! Критическая ошибка: {err}",
    "gui.log_resumed": "Продолжено.",
    "gui.log_paused": "Пауза.",
    "gui.log_skip_req": "Запрошен пропуск…",
    "gui.msg_stop_title": "Стоп",
    "gui.msg_stop_confirm": "Остановить? Прогресс сохранится.",
    "gui.log_stop_req": "Остановка…",
    "gui.log_verify": "=== Тест вложений ===",
    "gui.msg_log_title": "Лог",
    "gui.err_win_title": "Ошибки и события",
    "gui.btn_clear": "Очистить",
    "gui.msg_settings_loaded": "Настройки загружены из settings.json",
    "gui.summary_mode": "Режим:",
    "gui.summary_chat": "Chat:",
    "gui.summary_vk": "ВК:",
    "gui.summary_tg": "ТГ:",
    "gui.summary_bots": "Ботов:",
    "gui.summary_multichat": "мульти-чат",
    "gui.summary_tasks": "Задач: {n}",
}

# ---------------------------------------------------------------------------
#  English strings
# ---------------------------------------------------------------------------
_EN: dict[str, str] = {
    # ── gui.py — time formatting ──────────────────────────────────────────
    "time.h": "h",
    "time.m": "m",
    "time.s": "s",

    # ── gui.py — window ───────────────────────────────────────────────────
    "gui.window_title": "Replay — VK / Telegram → Telegram",

    # ── gui.py — tabs ─────────────────────────────────────────────────────
    "gui.tab_run": "  ▶ Run  ",
    "gui.tab_settings": "  ⚙ Settings  ",

    # ── gui.py — run tab — task selector ──────────────────────────────────
    "gui.task_label": "Task:",
    "gui.task_n": "Task {n}",

    # ── gui.py — run tab — control buttons ────────────────────────────────
    "gui.btn_start": "▶ Start",
    "gui.btn_pause": "⏸ Pause",
    "gui.btn_resume": "▶ Resume",
    "gui.btn_skip": "⏭ Skip",
    "gui.btn_stop": "⏹ Stop",
    "gui.btn_test": "🧪 Test",
    "gui.btn_errors": "🚨 Errors",
    "gui.btn_log": "📄 Log",
    "gui.reset_progress": "Start over",

    # ── gui.py — run tab — progress ───────────────────────────────────────
    "gui.progress_frame": "Progress",
    "gui.phase": "Phase: {v}",
    "gui.elapsed": "Elapsed: {v}",
    "gui.remaining": "Remaining: {v}",
    "gui.speed": "Speed: {v}/min",
    "gui.current": "Current: {v}",
    "gui.file": "File: {v}  ({k})",
    "gui.vk_label": "VK:",
    "gui.tg_label": "TG:",

    # ── gui.py — run tab — statistics ─────────────────────────────────────
    "gui.stats_frame": "Statistics",
    "gui.stat_text": "Text",
    "gui.stat_photo": "Photos",
    "gui.stat_sticker": "Stickers",
    "gui.stat_voice": "Voice",
    "gui.stat_video": "Video",
    "gui.stat_document": "Files",
    "gui.stat_header": "Headers",
    "gui.stat_placeholder": "Placeholders",
    "gui.stat_skipped": "Skipped",
    "gui.stat_errors": "Errors",
    "gui.stat_retries": "Retries",

    # ── gui.py — run tab — resources ──────────────────────────────────────
    "gui.res_frame": "Resources",
    "gui.res_ram": "RAM",
    "gui.res_cpu": "CPU",
    "gui.res_threads": "Threads",
    "gui.res_downloads": "Downloads",
    "gui.res_flood": "429",
    "gui.ram_mb": "{v} MB",

    # ── gui.py — run tab — log ────────────────────────────────────────────
    "gui.log_frame": "Log",

    # ── gui.py — settings tab ─────────────────────────────────────────────
    "gui.btn_add_task": "+ Add task",
    "gui.btn_save_settings": "💾 Save settings",
    "gui.btn_reload": "↻ Reload from file",
    "gui.btn_open_settings": "📂 Open settings.json",
    "gui.btn_validate": "🔍 Validate paths",

    # ── gui.py — task panel ───────────────────────────────────────────────
    "gui.task_name_label": "Name:",
    "gui.btn_delete_task": "✕ Delete task",
    "gui.target_frame": "Target Telegram chat",
    "gui.chat_id_hint": "(for supergroup: -100…)",
    "gui.mode_frame": "Send mode",
    "gui.multichat_label": "Multi-chat (one bot, [Name] before message)",
    "gui.vk_frame": "VKontakte — JSON export (+)",
    "gui.btn_add_vk": "+ Add VK JSON",
    "gui.tg_frame": "Telegram — export folders (+)",
    "gui.btn_add_tg": "+ Add TG folder",
    "gui.bots_frame": "Bots and senders",
    "gui.btn_add_bot": "+ Add bot",
    "gui.btn_detect": "🔍 Detect senders",
    "gui.att_frame": "Attachments (what to send)",
    "gui.rate_frame": "Speed and behavior",
    "gui.delay_label": "Delay, s:",
    "gui.attempts_label": "Media attempts:",
    "gui.date_headers": "Date headers",
    "gui.section_headers": "Section headers",
    "gui.placeholders_missing": "Placeholders for missing files",

    # ── gui.py — VkExportRow / TgExportRow / BotRow ───────────────────────
    "gui.row_json": "JSON:",
    "gui.row_folder": "Folder:",
    "gui.row_title": "Title:",
    "gui.row_bot_name": "Name:",
    "gui.row_bot_token": "Token:",
    "gui.row_bot_system": "Sys.",
    "gui.row_bot_default": "Default",
    "gui.row_bot_display": "Display:",
    "gui.row_bot_tg_names": "TG names:",

    # ── gui.py — default labels ───────────────────────────────────────────
    "gui.vk_default_label": "VK",
    "gui.vk_default_label_n": "VK {n}",
    "gui.tg_default_label": "Telegram",
    "gui.tg_default_label_n": "Telegram {n}",

    # ── gui.py — detect senders ───────────────────────────────────────────
    "gui.detected_vk": "VK senders: {v}",
    "gui.detected_tg": "TG senders: {v}",

    # ── gui.py — dialogs / messages ───────────────────────────────────────
    "gui.cannot_delete_last": "Cannot delete the only task.",
    "gui.dlg_tasks_title": "Tasks",
    "gui.settings_loaded": "Settings loaded from settings.json",
    "gui.load_error_title": "Error",
    "gui.load_error_msg": "Failed to load settings.json:\n{e}",
    "gui.save_warning_title": "Validation",
    "gui.save_warning_msg": "Saved, but there are warnings:\n\n{errs}",
    "gui.saved_log": "Settings saved: {path}",
    "gui.saved_title": "Saved",
    "gui.saved_msg": "Settings written to\n{path}",
    "gui.error_title": "Error",
    "gui.msg_error_title": "Error",
    "gui.msg_settings_load_err": "Failed to load settings.json:\n{err}",
    "gui.validate_ok_title": "Validation",
    "gui.validate_ok_msg": "All paths and parameters are OK ✓",
    "gui.validate_warn_title": "Validation",
    "gui.no_task_selected": "No task selected.",
    "gui.start_warning_title": "Warning",
    "gui.start_warning_msg": "There are issues with settings:\n\n{errs}\n\nRun anyway?",
    "gui.run_log_start": "=== Starting: {name} ===",
    "gui.critical_error": "!!! Critical error: {e}",
    "gui.paused_log": "Paused.",
    "gui.resumed_log": "Resumed.",
    "gui.skip_requested_log": "Skip requested…",
    "gui.stop_title": "Stop",
    "gui.stop_msg": "Stop? Progress will be saved.",
    "gui.stopping_log": "Stopping…",
    "gui.test_log": "=== Attachment test ===",
    "gui.log_title": "Log",
    "gui.file_title": "File",

    # ── gui.py — error window ─────────────────────────────────────────────
    "gui.err_window_title": "Errors and events",
    "gui.err_clear": "Clear",
    "gui.err_col_time": "Time",
    "gui.err_col_type": "Type",
    "gui.err_col_msg": "Message",
    "gui.err_count": "Events: {n}",

    # ── gui.py — language switcher ────────────────────────────────────────
    "gui.lang_label": "Lang:",

    # ── settings_manager.py — mode labels ─────────────────────────────────
    "mode.vk_only": "VKontakte only",
    "mode.tg_only": "Telegram only",
    "mode.vk_and_tg": "VK + Telegram",

    # ── settings_manager.py — attachment labels ───────────────────────────
    "att.photo": "Photos",
    "att.sticker": "Stickers",
    "att.voice": "Voice",
    "att.audio": "Audio",
    "att.video": "Video",
    "att.video_note": "Video notes",
    "att.animation": "GIF",
    "att.document": "Documents",
    "att.gift": "Gifts (VK)",

    # ── settings_manager.py — default names ───────────────────────────────
    "settings.default_task_name": "Task 1",
    "settings.default_task": "Task",
    "settings.default_vk_label": "VK",
    "settings.default_vk_label_n": "VK {n}",
    "settings.default_tg_label": "Telegram {n}",

    # ── settings_manager.py — validation errors ──────────────────────────
    "val.no_chat_id": "Target Chat ID not specified.",
    "val.no_vk_export": "No VK JSON export added.",
    "val.vk_not_found": "VK JSON not found: {path}",
    "val.no_tg_export": "Add at least one Telegram export folder.",
    "val.tg_dir_not_found": "Telegram folder not found: {path}",
    "val.tg_no_messages": "No messages*.html in folder: {path}",
    "val.no_bots": "No bots added.",
    "val.no_token": "No token specified for bot \"{key}\".",
    "val.multichat_bot_missing": "Multi-chat bot \"{bot}\" not found in bots list.",
    "val.delay_not_number": "Delay between messages must be a number.",

    # ── settings_manager.py — summaries ───────────────────────────────────
    "summary.mode": "Mode: {mode}",
    "summary.chat": "Chat: {chat}",
    "summary.vk_count": "VK: {n}",
    "summary.tg_count": "TG: {n}",
    "summary.bots_count": "Bots: {n}",
    "summary.multichat": "multi-chat",
    "summary.tasks_count": "Tasks: {n}",

    # ── run_export.py — date formatting ───────────────────────────────────
    "date.january": "January",
    "date.february": "February",
    "date.march": "March",
    "date.april": "April",
    "date.may": "May",
    "date.june": "June",
    "date.july": "July",
    "date.august": "August",
    "date.september": "September",
    "date.october": "October",
    "date.november": "November",
    "date.december": "December",
    "date.format": "{day} {month} {year}",

    # ── run_export.py — preview / phases ──────────────────────────────────
    "run.section_prefix": "── section {label} ──",
    "run.phase_vk": "VKontakte",
    "run.phase_tg": "Telegram",
    "run.empty": "(empty)",
    "run.done": "Done",

    # ── telegram_client.py — event log tags ───────────────────────────────
    "tag.no_network": "NO NET",
    "tag.network": "NET",
    "tag.server": "SERVER",
    "tag.error": "ERROR",
    "tag.gave_up": "GAVE UP",
    "tag.flood": "429",

    # ── telegram_client.py — event log messages ───────────────────────────
    "net.no_connection": "{method}: no connection, waiting for network ({err})",
    "net.attempt": "{method}: {err}: {msg} (attempt {n})",
    "net.gave_up_net": "{method}: skipping attachment after {n} failed attempts",
    "net.flood_wait": "{method}: flood control, waiting {sec}s",
    "net.server_error": "{method}: HTTP {code} (attempt {n})",
    "net.gave_up_server": "{method}: skipping attachment after {n} attempts (server)",

    # ── media.py — event log ──────────────────────────────────────────────
    "tag.link": "LINK",
    "tag.download": "DOWNLOAD",
    "media.external_link": "external link not downloaded: {url}",
    "media.gone": "VK media unavailable (HTTP {code})",
    "media.download_retry": "download: HTTP {code} (attempt {attempt}/{total})",
    "media.download_failed_http": "VK media: HTTP {code} after {total} attempts",
    "media.download_failed_err": "download failed [{err}] (attempt {attempt}/{total})",
    "media.download_gave_up": "VK media not downloaded [{err}] after {total} attempts",

    # ── vk_parser.py — placeholder notes ──────────────────────────────────
    "vk.photo_unavailable": "[photo unavailable]",
    "vk.photo": "[photo]",
    "vk.sticker": "[sticker]",
    "vk.graffiti": "[graffiti]",
    "vk.voice_msg": "[voice message, {dur}s]",
    "vk.gif": "[GIF]",
    "vk.image": "[image]",
    "vk.file": "[file: {name}]",
    "vk.video_title": "video",
    "vk.wall_repost": "[wall repost]",
    "vk.wall_comment": "[wall comment]",
    "vk.market_item": "[market item: {title}]",
    "vk.poll": "[poll: {question}]",
    "vk.gift": "🎁 [gift]",
    "vk.call": "[call]",
    "vk.story": "[story]",
    "vk.geo": "[geolocation]",
    "vk.attachment": "[attachment: {type}]",
    "vk.attachment_short": "attachment",
    "vk.reply_to": "↪ in reply to: \"{quote}\"",
    "vk.forwarded": "[forwarded]",

    # ── tg_parser.py — placeholder notes ──────────────────────────────────
    "tg.photo": "[photo]",
    "tg.sticker": "[sticker]",
    "tg.voice_msg": "[voice message{dur}]",
    "tg.video_note": "[video note]",
    "tg.video": "[video]",
    "tg.file": "[file: {name}]",
    "tg.reply": "↪ in reply",
    "tg.forwarded": "[forwarded{src}]",

    # ── tg_parser.py — call formatting ────────────────────────────────────
    "call.h": "h",
    "call.min": "min",
    "call.sec": "sec",
    "call.missed": "📞 Missed call",
    "call.cancelled": "📞 Cancelled call",
    "call.declined": "📞 Declined call",
    "call.call": "📞 Call",
    "call.unanswered": "📞 Call (unanswered)",
    "call.outgoing": "outgoing",
    "call.incoming": "incoming",
    "call.duration": "⏱ Duration: {dur}",

    # ── sender.py ─────────────────────────────────────────────────────────
    "sender.gift_label": "🎁 [gift]",

    # ── verify.py ─────────────────────────────────────────────────────────
    "verify.start_msg": "🔧 ATTACHMENT CHECK — sending all types.",
    "verify.text_bot1": "Text from bot 1 ✅",
    "verify.text_bot2": "Text from bot 2 ✅",
    "verify.sticker_fallback": "sticker (as photo, fallback)",
    "verify.real_vk_photo": "real VK photo",
    "verify.test_photo": "test photo",
    "verify.gif_animation": "GIF/animation",
    "verify.voice_msg": "voice message",
    "verify.audio_track": "audio track",
    "verify.video": "video",
    "verify.document": "document",
    "verify.real_vk_voice": "real VK voice message",
    "verify.real_vk_audio": "real VK audio",
    "verify.placeholder_example": "[voice message, 15s]\n(original unavailable — link expired)",
    "verify.done_msg": "🔧 CHECK COMPLETE.",
    "gui.title_label": "Title:",
    "gui.folder_label": "Folder:",
    "gui.name_label": "Name:",
    "gui.token_label": "Token:",
    "gui.system_bot_flag": "Sys",
    "gui.default_bot_flag": "Def",
    "gui.display_name_label": "Display:",
    "gui.tg_names_label": "TG names:",
    "gui.task_default_name": "Task {num}",
    "gui.delete_task_btn": "✕ Delete task",
    "gui.target_chat_frame": "Target Telegram chat",
    "gui.supergroup_hint": "(for supergroup: -100…)",
    "gui.multichat_cb": "Multi-chat (one bot, [Name] prefix)",
    "gui.add_vk_btn": "+ Add VK JSON",
    "gui.add_tg_btn": "+ Add TG folder",
    "gui.add_bot_btn": "+ Add bot",
    "gui.detect_senders_btn": "🔍 Detect senders",
    "gui.attachments_frame": "Attachments (what to send)",
    "gui.behavior_frame": "Rate and behavior",
    "gui.retries_label": "Media retries:",
    "gui.date_hdr_cb": "Date headers",
    "gui.sect_hdr_cb": "Section headers",
    "gui.placeholders_cb": "Placeholders for missing files",
    "gui.vk_senders_found": "VK senders: {senders}",
    "gui.tg_senders_found": "TG senders: {senders}",
    "gui.btn_reset": "Reset",
    "gui.frame_progress": "Progress",
    "gui.lbl_phase": "Phase:",
    "gui.lbl_elapsed": "Elapsed:",
    "gui.lbl_eta": "ETA:",
    "gui.lbl_rate": "Rate:",
    "gui.lbl_current": "Current:",
    "gui.lbl_file": "File:",
    "gui.lbl_vk": "VK:",
    "gui.lbl_tg": "TG:",
    "gui.rate_fmt": "Rate: {rate:.0f}/min",
    "gui.frame_stats": "Statistics",
    "gui.stat_placeholders": "Placeholders",
    "gui.frame_resources": "Resources",
    "gui.frame_log": "Log",
    "gui.add_task_btn": "+ Add task",
    "gui.save_settings_btn": "💾 Save settings",
    "gui.reload_settings_btn": "↻ Reload from file",
    "gui.open_settings_btn": "📂 Open settings.json",
    "gui.validate_paths_btn": "🔍 Validate paths",
    "gui.msg_tasks_title": "Tasks",
    "gui.msg_cannot_delete_last": "Cannot delete the only task.",
    "gui.msg_check_title": "Validation",
    "gui.msg_saved_warnings": "Saved, but with warnings:",
    "gui.msg_settings_saved_log": "Settings saved: {path}",
    "gui.msg_settings_saved": "Settings written to\n{path}",
    "gui.msg_check_ok": "All paths and parameters are OK ✓",
    "gui.msg_file_title": "File",
    "gui.msg_no_task_selected": "No task selected.",
    "gui.msg_warn_title": "Warning",
    "gui.msg_settings_issues": "Settings issues found:",
    "gui.msg_run_anyway": "Run anyway?",
    "gui.log_start": "=== Start: {name} ===",
    "gui.log_critical_err": "!!! Critical error: {err}",
    "gui.log_resumed": "Resumed.",
    "gui.log_paused": "Paused.",
    "gui.log_skip_req": "Skip requested...",
    "gui.msg_stop_title": "Stop",
    "gui.msg_stop_confirm": "Stop? Progress will be saved.",
    "gui.log_stop_req": "Stopping...",
    "gui.log_verify": "=== Attachment test ===",
    "gui.msg_log_title": "Log",
    "gui.err_win_title": "Errors and events",
    "gui.btn_clear": "Clear",
    "gui.msg_settings_loaded": "Settings loaded from settings.json",
    "gui.summary_mode": "Mode:",
    "gui.summary_chat": "Chat:",
    "gui.summary_vk": "VK:",
    "gui.summary_tg": "TG:",
    "gui.summary_bots": "Bots:",
    "gui.summary_multichat": "multi-chat",
    "gui.summary_tasks": "Tasks: {n}",
}

_DICTS = {"ru": _RU, "en": _EN}


def set_lang(lang: str) -> None:
    """Switch the active language ('ru' or 'en')."""
    global _LANG
    if lang in _DICTS:
        _LANG = lang


def get_lang() -> str:
    """Return the current language code."""
    return _LANG


def t(key: str, **kwargs) -> str:
    """Look up a translated string by key.

    Supports ``str.format`` keyword substitution::

        t("gui.task_n", n=3)      """
    d = _DICTS.get(_LANG, _RU)
    raw = d.get(key) or _RU.get(key) or key
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, IndexError):
            return raw
    return raw


def get_event_tags() -> list[tuple[str, str]]:
    """Return event-level tags and their colors for the error Treeview.

    Returns a list of (tag_string, color) tuples using the current language.
    """
    return [
        (t("tag.flood"), "#b06a00"),
        (t("tag.network"), "#0050b0"),
        (t("tag.no_network"), "#888800"),
        (t("tag.server"), "#7a00b0"),
        (t("tag.error"), "#b00000"),
        (t("tag.gave_up"), "#b00000"),
    ]


def get_mode_labels() -> dict[str, str]:
    """Return mode -> human label mapping for the current language."""
    return {
        "vk_only": t("mode.vk_only"),
        "tg_only": t("mode.tg_only"),
        "vk_and_tg": t("mode.vk_and_tg"),
    }


def get_attachment_labels() -> dict[str, str]:
    """Return attachment kind -> human label mapping for the current language."""
    return {
        "photo": t("att.photo"),
        "sticker": t("att.sticker"),
        "voice": t("att.voice"),
        "audio": t("att.audio"),
        "video": t("att.video"),
        "video_note": t("att.video_note"),
        "animation": t("att.animation"),
        "document": t("att.document"),
        "gift": t("att.gift"),
    }


def get_stat_items() -> list[tuple[str, str]]:
    """Return (stat_key, label) list for the statistics panel."""
    return [
        ("text", t("gui.stat_text")),
        ("photo", t("gui.stat_photo")),
        ("sticker", t("gui.stat_sticker")),
        ("voice", t("gui.stat_voice")),
        ("video", t("gui.stat_video")),
        ("document", t("gui.stat_document")),
        ("header", t("gui.stat_header")),
        ("placeholders", t("gui.stat_placeholder")),
        ("skipped", t("gui.stat_skipped")),
        ("errors", t("gui.stat_errors")),
        ("retries", t("gui.stat_retries")),
    ]


def get_res_items() -> list[tuple[str, str]]:
    """Return (res_key, label) list for the resources panel."""
    return [
        ("ram", t("gui.res_ram")),
        ("cpu", t("gui.res_cpu")),
        ("threads", t("gui.res_threads")),
        ("downloads", t("gui.res_downloads")),
        ("flood", t("gui.res_flood")),
    ]


def get_month_name(month: int) -> str:
    """Return the localized month name for date headers (1-12)."""
    keys = [
        "date.january", "date.february", "date.march", "date.april",
        "date.may", "date.june", "date.july", "date.august",
        "date.september", "date.october", "date.november", "date.december",
    ]
    if 1 <= month <= 12:
        return t(keys[month - 1])
    return ""


def format_date(year: int, month: int, day: int) -> str:
    """Format a date header using the current language's month names."""
    month_name = get_month_name(month)
    return t("date.format", day=day, month=month_name, year=year)
