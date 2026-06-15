"""Pre-flight verification: sends one of every attachment type to the target
chat so you can visually confirm rendering before the full replay.

It uses real data where possible (a real VK sticker, a real VK photo, a real
document from the Telegram export) and synthesizes small samples for the media
types whose originals are expired/missing (voice, audio, video, video note,
gif). Synthesis uses the ffmpeg binary bundled by imageio-ffmpeg.
"""
import glob
import os
import subprocess
import sys

from PIL import Image, ImageDraw

import config
import media
import models
import vk_parser
from telegram_client import get_bot, TelegramError

SAMPLES = os.path.join(config.CACHE_DIR, "verify_samples")
os.makedirs(SAMPLES, exist_ok=True)


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args) -> bool:
    try:
        subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", *args],
                       check=True)
        return True
    except Exception as e:
        print("  ffmpeg failed:", e)
        return False


def make_png() -> str:
    p = os.path.join(SAMPLES, "photo.png")
    img = Image.new("RGB", (600, 400), (40, 90, 160))
    d = ImageDraw.Draw(img)
    d.ellipse((150, 80, 450, 320), fill=(250, 210, 80))
    d.text((180, 360), "TEST PHOTO", fill=(255, 255, 255))
    img.save(p)
    return p


def make_gif() -> str:
    p = os.path.join(SAMPLES, "anim.gif")
    frames = []
    for i in range(12):
        im = Image.new("RGB", (240, 240), (20, 20, 30))
        d = ImageDraw.Draw(im)
        x = 20 + i * 15
        d.ellipse((x, 90, x + 60, 150), fill=(255, 100 + i * 10, 80))
        frames.append(im)
    frames[0].save(p, save_all=True, append_images=frames[1:],
                   duration=80, loop=0)
    return p


def make_sticker_webp() -> str:
    """Synthetic 512px webp with transparency (fallback if VK sticker fails)."""
    p = os.path.join(SAMPLES, "sticker.webp")
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((40, 40, 472, 472), fill=(255, 90, 140, 255))
    d.text((200, 240), ":)", fill=(255, 255, 255, 255))
    im.save(p, "WEBP", lossless=True)
    return p


def make_mp3() -> str | None:
    p = os.path.join(SAMPLES, "audio.mp3")
    ok = _run(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
               "-q:a", "9", p])
    return p if ok else None


def make_voice_ogg() -> str | None:
    p = os.path.join(SAMPLES, "voice.ogg")
    ok = _run(["-f", "lavfi", "-i", "sine=frequency=600:duration=2",
               "-c:a", "libopus", "-b:a", "32k", p])
    return p if ok else None


def make_mp4() -> str | None:
    p = os.path.join(SAMPLES, "video.mp4")
    ok = _run(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
               "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-shortest", p])
    return p if ok else None


def make_video_note() -> str | None:
    p = os.path.join(SAMPLES, "note.mp4")
    ok = _run(["-f", "lavfi", "-i", "testsrc=size=240x240:rate=15:duration=2",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", p])
    return p if ok else None


def find_vk_samples():
    """Pull real samples from the VK export: a sticker URL, a photo URL, and the
    locally-downloaded voice/audio/photo files (via the HTTrack media map)."""
    s = {"sticker_url": None, "photo_url": None,
         "voice_local": None, "audio_local": None, "photo_local": None}
    vk_path = config.VK_JSON
    if not vk_path or not os.path.isfile(vk_path):
        return s
    for e in vk_parser.parse(vk_path):
        for a in e.attachments:
            if a.kind == models.STICKER and a.url and not s["sticker_url"]:
                s["sticker_url"] = a.url
            if a.kind == models.PHOTO and a.url and a.url.startswith("http") and not s["photo_url"]:
                s["photo_url"] = a.url
            if a.kind == models.PHOTO and a.local_path and not s["photo_local"]:
                s["photo_local"] = a.local_path
            if a.kind == models.VOICE and a.local_path and not s["voice_local"]:
                s["voice_local"] = a.local_path
            if a.kind == models.AUDIO and a.local_path and not s["audio_local"]:
                s["audio_local"] = a.local_path
        if all(s.values()):
            break
    return s


def _get_bots():
    """Return up to two bots for testing. Uses first available bots from config."""
    keys = list(config.BOT_TOKENS.keys())
    if not keys:
        raise RuntimeError("No bots configured. Add at least one bot in settings.")
    bot1 = get_bot(keys[0])
    bot2 = get_bot(keys[1]) if len(keys) > 1 else bot1
    return bot1, bot2


def main():
    results = []

    def step(name, fn):
        try:
            fn()
            results.append((name, "OK"))
            print(f"[OK]   {name}")
        except Exception as e:
            results.append((name, f"FAIL: {e}"))
            print(f"[FAIL] {name}: {e}")

    bot1, bot2 = _get_bots()

    print("== getMe ==")
    for b in (bot1, bot2):
        me = b.get_me()
        print(f"  {b.name}: @{me.get('username')} (id {me['id']})")

    bot2.send_message("🔧 ПРОВЕРКА ВЛОЖЕНИЙ — начинаю отправку всех типов.")

    print("== building samples ==")
    vk = find_vk_samples()
    sticker_url, photo_url = vk["sticker_url"], vk["photo_url"]

    # 1. plain text from both bots
    step("text (bot1)", lambda: bot1.send_message("Текст от бота 1 ✅"))
    step("text (bot2)", lambda: bot2.send_message("Текст от бота 2 ✅"))

    # 2. sticker as a non-clickable image (the key requirement)
    def _sticker():
        path = media.to_sticker_webp(sticker_url) if sticker_url else None
        if not path:
            path = make_sticker_webp()
        try:
            bot1.send_sticker(path)
        except TelegramError:
            bot1.send_photo(path, "стикер (как фото, fallback)")
    step("sticker (VK -> sendSticker)", _sticker)

    # 2b. real Telegram animated stickers (.tgs Lottie and .webm video sticker)
    def _pick(folder, ext):
        if not config.TG_DIR:
            return None
        for p in sorted(glob.glob(os.path.join(config.TG_DIR, folder, "*" + ext))):
            if "_thumb" not in os.path.basename(p):
                return p
        return None

    def _tgs():
        p = _pick("stickers", ".tgs")
        if not p:
            raise RuntimeError("no .tgs sticker in export")
        bot2.send_sticker(p)
    step("sticker (TG .tgs animated)", _tgs)

    def _webm():
        p = _pick("video_files", ".webm")
        if not p:
            raise RuntimeError("no .webm sticker in export")
        bot1.send_sticker(p)
    step("sticker (TG .webm video)", _webm)

    # 3. real VK photo (download + upload)
    def _vkphoto():
        if not photo_url:
            raise RuntimeError("no VK photo url found")
        p = media.download(photo_url, "jpg")
        if not p:
            raise RuntimeError("VK photo download failed (URL expired?)")
        bot2.send_photo(p, "реальное фото из ВК")
    step("photo (real VK)", _vkphoto)

    # 4. generated photo
    step("photo (generated)", lambda: bot1.send_photo(make_png(), "тестовое фото"))

    # 5. animation / gif
    step("animation (gif)", lambda: bot2.send_animation(make_gif(), "GIF/анимация"))

    # 6. voice message
    def _voice():
        p = make_voice_ogg()
        if not p:
            raise RuntimeError("ffmpeg could not make ogg/opus")
        bot1.send_voice(p, "голосовое сообщение", 2)
    step("voice (ogg/opus)", _voice)

    # 7. audio track
    def _audio():
        p = make_mp3()
        if not p:
            raise RuntimeError("ffmpeg could not make mp3")
        bot2.send_audio(p, "аудио-трек", title="Test Track", performer="Verifier", duration=2)
    step("audio (mp3)", _audio)

    # 8. video
    def _video():
        p = make_mp4()
        if not p:
            raise RuntimeError("ffmpeg could not make mp4")
        bot1.send_video(p, "видео", 2)
    step("video (mp4)", _video)

    # 9. round video note
    def _note():
        p = make_video_note()
        if not p:
            raise RuntimeError("ffmpeg could not make note mp4")
        bot2.send_video_note(p)
    step("video_note (round)", _note)

    # 10. document (real file from the Telegram export if present, else generated)
    def _doc():
        real = None
        if config.TG_FILES_DIR and os.path.isdir(config.TG_FILES_DIR):
            for f in os.listdir(config.TG_FILES_DIR):
                real = os.path.join(config.TG_FILES_DIR, f)
                break
        if not real:
            real = os.path.join(SAMPLES, "sample.txt")
            open(real, "w", encoding="utf-8").write("sample document")
        bot2.send_document(real, "документ")
    step("document", _doc)

    # 10b. REAL VK voice message (local mp3 -> opus -> voice bubble)
    def _vkvoice():
        if not vk["voice_local"]:
            raise RuntimeError("no local VK voice found")
        ogg = media.mp3_to_opus(vk["voice_local"])
        if not ogg:
            raise RuntimeError("mp3->opus conversion failed")
        bot1.send_voice(ogg, "реальное голосовое из ВК", 0)
    step("voice (real VK local mp3->opus)", _vkvoice)

    # 10c. REAL VK audio track (local mp3)
    def _vkaudio():
        if not vk["audio_local"]:
            raise RuntimeError("no local VK audio found")
        bot2.send_audio(vk["audio_local"], "реальное аудио из ВК")
    step("audio (real VK local)", _vkaudio)

    # 11. placeholder example (how missing media will look in the real run)
    step("placeholder example",
         lambda: bot1.send_message("[голосовое сообщение, 15с]\n(оригинал недоступен — ссылка истекла)"))

    bot2.send_message("🔧 ПРОВЕРКА ЗАВЕРШЕНА.")

    print("\n==== SUMMARY ====")
    ok = sum(1 for _, s in results if s == "OK")
    for name, s in results:
        print(f"  {name}: {s}")
    print(f"\n{ok}/{len(results)} checks OK")
    if ok != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
