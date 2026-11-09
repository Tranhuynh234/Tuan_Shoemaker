"""Cấu hình ứng dụng. Mọi giá trị nhạy cảm đọc từ biến môi trường / file .env."""
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _ssl_connect_args() -> dict:
    """Aiven yêu cầu SSL. CA đọc từ DB_SSL_CA (đường dẫn file) hoặc DB_SSL_CA_PEM (nội dung)."""
    ca_path = os.getenv("DB_SSL_CA")
    ca_pem = os.getenv("DB_SSL_CA_PEM")
    if ca_pem:
        p = Path(tempfile.gettempdir()) / "aiven-ca.pem"
        p.write_text(ca_pem.replace("\\n", "\n"))
        ca_path = str(p)
    if ca_path:
        return {"ssl": {"ca": ca_path}}
    return {}


def _build_db_uri() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("DB_USER", "root")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "giaytuan")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _build_db_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "connect_args": _ssl_connect_args(),
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    CSRF_ENABLED = True

    # Upload ảnh
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    PRODUCT_FORM_MAX_BYTES = 64 * 1024 * 1024  # form sản phẩm: tối đa 12 ảnh x 5MB gửi cùng lúc
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads" / "products")
    BLOG_UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads" / "blog")
    # Tên khóa phải là ALLOWED_IMAGE_EXTENSIONS: app/utils/uploads.py đọc đúng khóa này
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Nghiệp vụ
    SHIPPING_FEE = int(os.getenv("SHIPPING_FEE", "30000"))
    FREE_SHIPPING_THRESHOLD = int(os.getenv("FREE_SHIPPING_THRESHOLD", "1000000"))
    MAX_QTY_PER_ITEM = 20
    PRODUCTS_PER_PAGE = 9
    ADMIN_PER_PAGE = 20
    # Chỉ COD được kích hoạt. Thêm phương thức online chỉ sau khi tích hợp và xác minh nhà cung cấp.
    ENABLED_PAYMENT_METHODS = ("COD",)

    # Đăng nhập bằng SĐT: giới hạn thử sai
    LOGIN_MAX_FAILS_PER_PHONE = int(os.getenv("LOGIN_MAX_FAILS_PER_PHONE", "5"))   
    LOGIN_MAX_FAILS_PER_IP = int(os.getenv("LOGIN_MAX_FAILS_PER_IP", "20"))       
    LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))   
    REGISTER_MAX_PER_IP_HOUR = int(os.getenv("REGISTER_MAX_PER_IP_HOUR", "10"))
    GUEST_ORDER_MAX_PER_IP_HOUR = int(os.getenv("GUEST_ORDER_MAX_PER_IP_HOUR", os.getenv("GUEST_CHECKOUT_MAX_PER_IP_HOUR", "20")))
    GUEST_ORDER_MAX_PER_PHONE_HOUR = int(os.getenv("GUEST_ORDER_MAX_PER_PHONE_HOUR", "5"))

    # OTP khôi phục mật khẩu qua SMS
    OTP_TTL_SECONDS = 300
    OTP_RESEND_COOLDOWN = 60
    OTP_MAX_ATTEMPTS = 5
    OTP_MAX_SENDS_PER_PHONE_HOUR = 5
    OTP_MAX_SENDS_PER_IP_HOUR = 10
    OTP_MAX_VERIFY_PER_PHONE = 10      # trong 15 phút
    OTP_MAX_VERIFY_PER_IP = 30         # trong 15 phút
    RESET_TOKEN_TTL_SECONDS = 600

    # Nhà cung cấp SMS (để trống = CHƯA gửi được OTP thật). Giá trị: esms | speedsms
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "")
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    SMS_API_SECRET = os.getenv("SMS_API_SECRET", "")
    SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "")
    SMS_TYPE = os.getenv("SMS_TYPE", "2")
    SMS_SANDBOX = os.getenv("SMS_SANDBOX", "0") == "1"
    SMS_TIMEOUT = int(os.getenv("SMS_TIMEOUT", "10"))
    SMS_OTP_TEMPLATE = os.getenv("SMS_OTP_TEMPLATE", "TUAN: Ma OTP cua ban la {code}. Het han sau {minutes} phut. Khong chia se ma nay.")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-secret-key"
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CSRF_ENABLED = False
    SMS_PROVIDER = "memory"
    UPLOAD_FOLDER = str(BASE_DIR / "tests" / "_uploads")
    BLOG_UPLOAD_FOLDER = str(BASE_DIR / "tests" / "_uploads_blog")


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}