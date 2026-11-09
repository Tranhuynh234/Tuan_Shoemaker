"""Dịch tự động (vi -> en / zh) cho những câu chưa có trong từ điển i18n.

Bật bằng biến môi trường (file .env):
  TRANSLATE_PROVIDER=anthropic   + ANTHROPIC_API_KEY=...   (TRANSLATE_MODEL tùy chọn)
  hoặc
  TRANSLATE_PROVIDER=google      + GOOGLE_TRANSLATE_API_KEY=...
  hoặc (KHÔNG cần key, dùng ngay)
  TRANSLATE_PROVIDER=free        (dịch vụ dịch công khai không chính thức: có thể bị giới hạn tốc độ hoặc ngừng
                                  hoạt động bất kỳ lúc nào; chất lượng trung bình. Nên dùng khi thử, web thật nên dùng key.)
Để trống TRANSLATE_PROVIDER = tắt (câu chưa có trong từ điển giữ tiếng Việt).

Mỗi câu chỉ dịch MỘT lần: kết quả lưu vào instance/translations_cache.json (đổi đường dẫn bằng TRANSLATE_CACHE).
Cả trang được gộp thành 1 request; lỗi mạng/quá thời gian thì giữ tiếng Việt, không làm hỏng trang.
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait

log = logging.getLogger(__name__)

LANG_NAMES = {"en": "English", "zh": "Simplified Chinese"}
GOOGLE_CODES = {"en": "en", "zh": "zh-CN"}
BATCH = 40
TIMEOUT = float(os.environ.get("TRANSLATE_TIMEOUT", "12"))

# Chờ tối đa WAIT giây mỗi lần mở trang; phần chưa dịch xong vẫn chạy nền và lưu cache cho lần mở sau.
WAIT = float(os.environ.get("TRANSLATE_WAIT", "4"))
MAX_PIECE = 1500                 # đoạn dài hơn được cắt theo câu để dịch vụ miễn phí không từ chối
FREE_BATCH = 8                   # số câu mỗi lượt cho chế độ free (gọi tuần tự, tránh bị giới hạn tốc độ)

_lock = threading.RLock()
_cache = None
_executor = ThreadPoolExecutor(max_workers=int(os.environ.get("TRANSLATE_WORKERS", "4")),
                               thread_name_prefix="translate")
_local = threading.local()      # _local.wait: luồng dịch sẵn (warm) được chờ lâu, không giới hạn WAIT
_blocked_until = 0.0             # dịch vụ free trả 429: tạm ngừng gọi tới mốc này (giây epoch) để không làm chậm trang
BLOCK_SECONDS = int(os.environ.get("TRANSLATE_BLOCK_SECONDS", "900"))
_inflight = {}                   # (lang, câu) -> future đang dịch, tránh dịch trùng khi nhiều người mở cùng lúc


def enabled() -> bool:
    return os.environ.get("TRANSLATE_PROVIDER", "").strip().lower() in ("anthropic", "google", "free")


def _path() -> str:
    return os.environ.get("TRANSLATE_CACHE") or os.path.join(os.getcwd(), "instance", "translations_cache.json")


def _key(lang: str, text: str) -> str:
    return lang + ":" + hashlib.sha1(text.encode("utf-8")).hexdigest()


def _load():
    global _cache
    if _cache is None:
        try:
            with open(_path(), encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save():
    path = _path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("Không lưu được cache dịch: %s", exc)


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _anthropic(texts, lang):
    system = (
        "You translate text for a Vietnamese shoe-shop website (Giày Tuấn). Translate each Vietnamese string into "
        f"{LANG_NAMES[lang]}. Keep brand names (Tuấn, Giày Tuấn, TUẤN, Kodoss...), numbers, currency, codes and "
        "leading symbols (like •, ★) unchanged. Keep the same UPPER/lower case style. Reply with ONLY a JSON array "
        "of strings, same length and same order as the input, no commentary."
    )
    data = _post("https://api.anthropic.com/v1/messages", {
        "model": os.environ.get("TRANSLATE_MODEL", "claude-haiku-5-5"), "max_tokens": 4000, "system": system,
        "messages": [{"role": "user", "content": json.dumps(texts, ensure_ascii=False)}],
    }, {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01"})
    out = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    out = out.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(out)


def _google(texts, lang):
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
    data = _post(f"https://translation.googleapis.com/language/translate/v2?key={key}",
                 {"q": texts, "source": "vi", "target": GOOGLE_CODES[lang], "format": "text"}, {})
    return [t["translatedText"] for t in data["data"]["translations"]]


def _split(text):
    """Cắt đoạn dài thành các mảnh <= MAX_PIECE ký tự, ưu tiên ngắt ở cuối câu."""
    if len(text) <= MAX_PIECE:
        return [text]
    pieces, cur = [], ""
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        while len(sent) > MAX_PIECE:
            cut = sent.rfind(" ", 0, MAX_PIECE)
            if cut <= 0:
                cut = MAX_PIECE
            if cur:
                pieces.append(cur)
                cur = ""
            pieces.append(sent[:cut])
            sent = sent[cut:].lstrip()
        if cur and len(cur) + 1 + len(sent) > MAX_PIECE:
            pieces.append(cur)
            cur = sent
        else:
            cur = (cur + " " + sent).strip()
    if cur:
        pieces.append(cur)
    return pieces


def _free_one(text, lang):
    global _blocked_until
    if time.time() < _blocked_until:             # đang bị dịch vụ chặn tạm: bỏ qua ngay, không chờ
        return None
    body = urllib.parse.urlencode({"client": "gtx", "sl": "vi", "tl": GOOGLE_CODES[lang], "dt": "t", "q": text}).encode()
    last = None
    for attempt in range(3):                     # thử lại có chờ tăng dần khi lỗi tạm thời
        try:
            req = urllib.request.Request("https://translate.googleapis.com/translate_a/single", data=body,
                                         headers={"User-Agent": "Mozilla/5.0"}, method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            out = "".join(seg[0] for seg in data[0] if seg and seg[0])
            if out.strip():
                return out
            last = ValueError("kết quả rỗng")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:                  # bị giới hạn tốc độ: thử lại chỉ làm bị chặn lâu hơn
                with _lock:
                    first = time.time() >= _blocked_until
                    _blocked_until = time.time() + BLOCK_SECONDS
                if first:
                    log.warning("Dịch vụ dịch miễn phí đang chặn tạm (HTTP 429). Tạm ngừng gọi %d phút; "
                                "nên dùng TRANSLATE_PROVIDER=anthropic hoặc google có key.", BLOCK_SECONDS // 60)
                return None
        except Exception as exc:
            last = exc
        time.sleep(0.6 * (2 ** attempt))
    log.warning("Dịch tự động (free) lỗi sau 3 lần thử (%d ký tự): %s", len(text), last)
    return None


def _free(texts, lang):
    out = []
    for text in texts:
        done = []
        for piece in _split(text):
            r = _free_one(piece, lang)
            if r is None:
                done = None
                break
            done.append(r)
        out.append(None if done is None else ("" if lang == "zh" else " ").join(done))
    return out


def _work(chunk, lang, provider):
    call = {"anthropic": _anthropic, "google": _google, "free": _free}[provider]
    try:
        out = call(chunk, lang)
        if not isinstance(out, list) or len(out) != len(chunk):
            raise ValueError("số câu dịch không khớp")
    except Exception as exc:  # mạng lỗi / hết hạn mức / sai key: giữ tiếng Việt, lần mở sau thử lại
        log.warning("Dịch tự động thất bại (%s): %s", provider, exc)
        return
    with _lock:
        cache = _load()
        for src, dst in zip(chunk, out):
            if isinstance(dst, str) and dst.strip():
                cache[_key(lang, src)] = dst.strip()
        _save()


def _release(lang, chunk):
    with _lock:
        for t in chunk:
            _inflight.pop((lang, t), None)


def translate_batch(texts, lang):
    """Trả về {câu_việt: bản_dịch}. Đọc cache trước; câu mới được dịch song song, chờ tối đa WAIT giây.
    Câu chưa kịp dịch tiếp tục chạy nền và lưu cache, lần mở trang sau sẽ có đủ.
    Luồng dịch sẵn (warm_blog) chờ đến khi xong và thử lại câu lỗi tới 3 vòng."""
    if not enabled() or lang not in LANG_NAMES:
        return {}
    provider = os.environ.get("TRANSLATE_PROVIDER", "").strip().lower()
    wait_s = getattr(_local, "wait", WAIT)
    with _lock:
        cache = _load()
        result = {t: cache[_key(lang, t)] for t in texts if _key(lang, t) in cache}
    todo = [t for t in texts if t not in result]
    size = FREE_BATCH if provider == "free" else BATCH
    for _ in range(3 if wait_s >= 60 else 1):
        if not todo:
            break
        with _lock:
            fresh = [t for t in todo if (lang, t) not in _inflight]
            for i in range(0, len(fresh), size):
                chunk = fresh[i:i + size]
                fut = _executor.submit(_work, chunk, lang, provider)
                for t in chunk:
                    _inflight[(lang, t)] = fut
                fut.add_done_callback(lambda f, c=chunk: _release(lang, c))
            futures = list({id(f): f for f in (_inflight.get((lang, t)) for t in todo) if f is not None}.values())
        if futures:
            wait(futures, timeout=wait_s)
        with _lock:
            cache = _load()
            result.update({t: cache[_key(lang, t)] for t in todo if _key(lang, t) in cache})
        todo = [t for t in todo if t not in result]
    if todo and wait_s >= 60:
        log.warning("Còn %d câu chưa dịch được sang %s (dịch vụ từ chối hoặc lỗi mạng)", len(todo), lang)
    return result


def warm_blog(app, slug=None):
    """Dịch sẵn (chạy nền) sang en + zh để khách mở là có ngay.
    slug=None: cả website (trang tĩnh, sản phẩm, blog); truyền slug: chỉ bài blog đó (gọi sau khi admin lưu bài)."""
    if not enabled():
        return

    def run():
        try:
            from sqlalchemy import select
            from app.models import BlogPost, Product
            from app.models.constants import POST_PUBLISHED
            _local.wait = 900
            with app.app_context():
                from app.extensions import db
                if slug:      # chỉ một bài blog vừa được admin lưu
                    paths = ["/blog", f"/blog/{slug}"]
                else:         # cả website: trang tĩnh, mọi sản phẩm đang bán, mọi bài blog đã đăng
                    paths = ["/", "/about", "/portfolio", "/products", "/blog", "/contact", "/cart/"]
                    paths += [f"/products/{x}" for x in db.session.scalars(
                        select(Product.slug).where(Product.is_active.is_(True)))]
                    paths += [f"/blog/{x}" for x in db.session.scalars(
                        select(BlogPost.slug).where(BlogPost.status == POST_PUBLISHED))]
                client = app.test_client()
                for lang in LANG_NAMES:
                    client.set_cookie("lang", lang)
                    for path in paths:
                        t0 = time.time()
                        resp = client.get(path)
                        log.info("Dịch sẵn %s [%s]: HTTP %s, %.1fs", path, lang, resp.status_code, time.time() - t0)
        except Exception:
            log.exception("Dịch sẵn blog thất bại")

    threading.Thread(target=run, daemon=True, name="translate-warm").start()