"""Chẩn đoán dịch blog: python diag_blog.py [slug-bài-blog]"""
import html as _html
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
from sqlalchemy import select

from app import auto_translate, create_app
from app.extensions import db
from app.i18n import HAS_VI, TEXT_NODE, _needs_auto
from app.models import BlogPost

app = create_app()
with app.app_context():
    slug = sys.argv[1] if len(sys.argv) > 1 else db.session.scalars(select(BlogPost.slug)).first()
    print("Bài blog:", slug)
    c = app.test_client()
    c.set_cookie("lang", "vi")
    resp = c.get(f"/blog/{slug}")
    print("HTTP", resp.status_code)
    raw = resp.get_data(as_text=True)
    keys = {" ".join(_html.unescape(m.group(1)).split()) for m in TEXT_NODE.finditer(raw)}
    pend = sorted(k for k in keys if HAS_VI.search(k) and _needs_auto(k, "en"))
    print(f"Cần dịch: {len(pend)} câu; câu dài nhất: {max(map(len, pend), default=0)} ký tự")
    t = time.time()
    out = auto_translate.translate_batch(pend, "en")
    print(f"Dịch được {len(out)}/{len(pend)} câu trong {time.time() - t:.1f}s")
    for k in [k for k in pend if k not in out][:8]:
        print(f"  THIẾU ({len(k)} ký tự): {k[:90]}")