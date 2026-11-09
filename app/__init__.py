import json
import logging
import mimetypes
import os
import secrets

import click
from flask import Flask, g, jsonify, render_template, request, session
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import CONFIGS, DevelopmentConfig

from .extensions import db, login_manager, migrate

# Windows đôi khi map sai đuôi video trong registry; kèm header nosniff thì trình duyệt sẽ từ chối phát.
for _ext, _mime in ((".mp4", "video/mp4"), (".webm", "video/webm"), (".mov", "video/quicktime")):
    mimetypes.add_type(_mime, _ext)


@event.listens_for(Engine, "connect")
def _sqlite_enable_fk(dbapi_connection, _record):
    """SQLite mặc định tắt khóa ngoại; bật lên để môi trường test hành xử giống MySQL."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(config=None):
    app = Flask(__name__)
    if isinstance(config, type):
        cfg = config
    else:
        cfg = CONFIGS.get(config or os.getenv("APP_ENV", "development"), DevelopmentConfig)
    app.config.from_object(cfg)

    if not app.config.get("SECRET_KEY"):
        if app.config.get("DEBUG") or app.config.get("TESTING"):
            app.config["SECRET_KEY"] = secrets.token_hex(32)
            app.logger.warning("SECRET_KEY chưa được đặt: dùng khóa tạm (phiên đăng nhập mất khi khởi động lại).")
        else:
            raise RuntimeError("Thiếu SECRET_KEY. Hãy đặt trong file .env.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (đăng ký model cho SQLAlchemy/Migrate)

    from .routes import register_blueprints
    register_blueprints(app)
    _register_hooks(app)
    _register_errors(app)
    _register_cli(app)
    return app


def _register_hooks(app):
    from .models.constants import (CONTACT_STATUS_LABELS, ORDER_STATUS_LABELS, PAYMENT_STATUS_LABELS)
    from .services import cart_service, catalog_service
    from .i18n import DEFAULT_LANG, LANGS, translate_html, translate_json
    from .utils import formatting
    from .utils.csrf import generate_csrf_token, protect_csrf

    @app.before_request
    def detect_language():
        lang = request.cookies.get("lang", DEFAULT_LANG)
        g.lang = lang if lang in LANGS else DEFAULT_LANG

    @app.before_request
    def allow_big_product_form():
        """Form sản phẩm gửi nhiều ảnh cùng lúc nên được nâng giới hạn dung lượng (từng ảnh vẫn tối đa 5MB)."""
        if request.method == "POST" and request.path.startswith("/admin/products"):
            try:
                request.max_content_length = app.config.get("PRODUCT_FORM_MAX_BYTES", 64 * 1024 * 1024)
            except AttributeError:  # Flask < 3.1 không cho đổi theo từng request
                pass

    app.before_request(protect_csrf)
    app.jinja_env.globals["csrf_token"] = generate_csrf_token  # dùng được cả trong macro
    app.jinja_env.filters.update(vnd=formatting.vnd, paragraphs=formatting.paragraphs, dt=formatting.dt,
                                 order_status=formatting.order_status_label,
                                 payment_status=formatting.payment_status_label,
                                 contact_status=formatting.contact_status_label)

    @app.context_processor
    def inject_globals():
        ctx = {"lang": g.get("lang", DEFAULT_LANG), "ORDER_STATUS_LABELS": ORDER_STATUS_LABELS,
               "PAYMENT_STATUS_LABELS": PAYMENT_STATUS_LABELS, "CONTACT_STATUS_LABELS": CONTACT_STATUS_LABELS,
               "menu_categories": catalog_service.active_categories(),
               "category_tree": catalog_service.CATEGORY_TREE, "cart_count": 0}
        if current_user.is_authenticated and not current_user.is_admin:
            ctx["cart_count"] = cart_service.cart_quantity(current_user)
        elif not current_user.is_authenticated:
            ctx["cart_count"] = sum(max(0, int(item.get("quantity", 0))) for item in session.get("guest_cart", [])
                                   if isinstance(item, dict))
        return ctx

    @app.before_request
    def warm_translations_once():
        """Lần có yêu cầu đầu tiên sau khi bật server: dịch sẵn các bài blog ở nền (không làm chậm khách)."""
        from . import auto_translate as _at
        if app.config.get("_warm_started") or app.testing or not _at.enabled():
            return
        app.config["_warm_started"] = True
        _at.warm_blog(app)

    @app.after_request
    def translate_response(resp):
        """Khi chọn tiếng Anh / Trung: dịch HTML các trang khách hàng (trang admin giữ tiếng Việt)."""
        lang = g.get("lang", DEFAULT_LANG)
        if (lang != DEFAULT_LANG and resp.mimetype == "text/html" and not resp.direct_passthrough
                and request.blueprint != "admin"):
            resp.set_data(translate_html(resp.get_data(as_text=True), lang))
        elif (lang != DEFAULT_LANG and resp.mimetype == "application/json" and not resp.direct_passthrough
                and request.blueprint != "admin"):
            try:
                resp.set_data(json.dumps(translate_json(resp.get_json(silent=True), lang), ensure_ascii=False))
            except Exception:  # không dịch được thì trả nguyên bản tiếng Việt
                pass
        return resp

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp


def _register_errors(app):
    messages = {
        400: ("Yêu cầu không hợp lệ", "Phiên làm việc không hợp lệ hoặc dữ liệu gửi lên không đúng. Vui lòng tải lại trang."),
        403: ("Không có quyền truy cập", "Bạn không có quyền thực hiện thao tác này."),
        404: ("Không tìm thấy trang", "Trang bạn tìm không tồn tại hoặc đã bị di chuyển."),
        413: ("Tệp quá lớn", "Dung lượng tệp tải lên vượt quá giới hạn cho phép (mỗi ảnh tối đa 5 MB)."),
        500: ("Đã xảy ra lỗi", "Hệ thống gặp sự cố. Vui lòng thử lại sau."),
    }

    def make_handler(code):
        def handler(err):
            if code == 500:
                db.session.rollback()
            title, text = messages[code]
            if code == 400 and getattr(err, "description", None) and "Phiên" in str(err.description):
                text = err.description
            if request.is_json or request.path.startswith("/api/"):  # fetch/JSON: trả JSON để trang hiện đúng lỗi
                return jsonify({"error": text}), code
            return render_template("error.html", code=code, title=title, message=text), code
        return handler

    for code in messages:
        app.register_error_handler(code, make_handler(code))


def _register_cli(app):
    from .models import User
    from .models.constants import ROLE_ADMIN
    from .utils.validators import normalize_phone, valid_phone, validate_password

    @app.cli.command("seed")
    @click.option("--demo", is_flag=True, help="Thêm sản phẩm/bài viết DEMO để thử giao diện.")
    def seed_command(demo):
        from database.seed import run_seed
        run_seed(demo=demo)

    @app.cli.command("sync-categories")
    def sync_categories_command():
        """Thêm các danh mục (giày tây, giày lười, sandal...) còn thiếu vào database."""
        from .services import catalog_service
        created = catalog_service.sync_categories()
        click.echo("Đã thêm: " + ", ".join(created) if created else "Danh mục đã đầy đủ, không có gì để thêm.")

    @app.cli.command("translate-check")
    def translate_check_command():
        """Thử dịch 1 câu để biết dịch tự động đã chạy được chưa (hiện lỗi thật nếu có)."""
        from .i18n import auto_translate
        provider = os.environ.get("TRANSLATE_PROVIDER", "")
        click.echo(f"TRANSLATE_PROVIDER = {provider!r}")
        if not auto_translate.enabled():
            raise click.ClickException("Chưa bật: thêm TRANSLATE_PROVIDER=free vào file .env rồi chạy lại.")
        call = {"anthropic": auto_translate._anthropic, "google": auto_translate._google,
                "free": auto_translate._free}[provider]
        sample = ["Quy trình sản xuất giày da chuẩn mực"]
        for lang in ("en", "zh"):
            try:
                out = call(sample, lang)
            except Exception as exc:
                raise click.ClickException(f"Gọi dịch thất bại ({lang}): {exc!r}")
            click.echo(f"[{lang}] {out}")
            if not out or out[0] is None:
                raise click.ClickException("Dịch vụ không trả kết quả (có thể bị chặn mạng hoặc giới hạn tốc độ).")
        click.echo("OK: dịch tự động hoạt động.")

    @app.cli.command("translate-site")
    @click.option("--lang", "langs", multiple=True, default=("en", "zh"), help="Ngôn ngữ cần dịch (mặc định en và zh).")
    def translate_site_command(langs):
        """Mở lần lượt mọi trang khách hàng (kể cả từng sản phẩm, từng bài blog) để dịch và lưu cache một lượt."""
        from sqlalchemy import select
        from .i18n import auto_translate
        from .models import BlogPost, Product
        from .models.constants import POST_PUBLISHED
        from .services.catalog_service import CATEGORY_TREE
        if not auto_translate.enabled():
            raise click.ClickException("Chưa bật dịch tự động: đặt TRANSLATE_PROVIDER và API key trong .env.")
        auto_translate.WAIT = 900  # lệnh này phải chờ dịch xong từng trang
        app.config["_warm_started"] = True  # tự lệnh này đã dịch hết, không cần dịch sẵn nền
        urls = ["/", "/about", "/portfolio", "/products", "/blog", "/contact", "/auth/login", "/login", "/register",
                "/forgot-password", "/cart/"]
        urls += [f"/products?category={g['slug']}" for g in CATEGORY_TREE]
        urls += [f"/products?category={slug}" for g in CATEGORY_TREE for _, slug in g["items"]]
        urls += [f"/products?page={n}" for n in (2, 3, 4)]
        urls += [f"/products/{slug}" for slug in db.session.scalars(select(Product.slug).where(Product.is_active.is_(True)))]
        urls += [f"/blog/{slug}" for slug in db.session.scalars(
            select(BlogPost.slug).where(BlogPost.status == POST_PUBLISHED))]
        ok = fail = 0
        client = app.test_client()
        for lang in langs:
            client.set_cookie("lang", lang)
            for url in urls:
                resp = client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    ok += 1
                else:
                    fail += 1
                    click.echo(f"  bỏ qua {url} ({resp.status_code})")
            click.echo(f"[{lang}] xong {len(urls)} địa chỉ.")
        click.echo(f"Hoàn tất: {ok} trang dịch được, {fail} trang bỏ qua. Cache: {auto_translate._path()}")

    @app.cli.command("create-admin")
    @click.option("--phone", default=None, help="Số điện thoại quản trị viên.")
    @click.option("--name", default="Quản trị viên")
    @click.option("--password", default=None, help="Nên bỏ trống để nhập ẩn khi chạy lệnh.")
    @click.option("--promote", is_flag=True, help="Nâng quyền cho số điện thoại đã tồn tại.")
    def create_admin(phone, name, password, promote):
        """Tạo hoặc nâng quyền ADMIN bằng số điện thoại."""
        phone = normalize_phone(phone or os.getenv("ADMIN_PHONE") or click.prompt("Số điện thoại admin"))
        if not valid_phone(phone):
            raise click.ClickException("Số điện thoại Việt Nam không hợp lệ.")
        existing = User.query.filter_by(phone=phone).first()
        if existing and not promote:
            raise click.ClickException("Số điện thoại đã tồn tại. Dùng --promote để nâng quyền.")
        if existing:
            existing.role, existing.is_active = ROLE_ADMIN, True
            db.session.commit()
            click.echo(f"Đã nâng quyền ADMIN cho {phone}.")
            return
        password = password or os.getenv("ADMIN_PASSWORD") or click.prompt(
            "Mật khẩu", hide_input=True, confirmation_prompt=True)
        err = validate_password(password)
        if err:
            raise click.ClickException(err)
        user = User(full_name=name, phone=phone, role=ROLE_ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Đã tạo ADMIN: {phone}")