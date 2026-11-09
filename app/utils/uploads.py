"""Kiểm tra và lưu ảnh upload: phần mở rộng, dung lượng, chữ ký file, tên file ngẫu nhiên."""
import os
import uuid

from flask import current_app

SIGNATURES = {
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),
}


MAX_IMAGE_BYTES = 5 * 1024 * 1024


class UploadError(Exception):
    pass


def _save_image(file_storage, folder: str, url_prefix: str) -> str:
    if not file_storage or not file_storage.filename:
        raise UploadError("Chưa chọn ảnh.")
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise UploadError("Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP.")
    file_storage.stream.seek(0, 2)
    if file_storage.stream.tell() > MAX_IMAGE_BYTES:
        raise UploadError("Ảnh lớn hơn 5MB.")
    file_storage.stream.seek(0)
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in SIGNATURES[ext]) or (ext == "webp" and head[8:12] != b"WEBP"):
        raise UploadError("Nội dung file không phải ảnh hợp lệ.")
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{'jpg' if ext == 'jpeg' else ext}"
    file_storage.save(os.path.join(folder, name))
    return f"{url_prefix}/{name}"


def save_product_image(file_storage) -> str:
    """Lưu ảnh sản phẩm, trả về đường dẫn tương đối trong static (vd: uploads/products/xxx.jpg)."""
    return _save_image(file_storage, current_app.config["UPLOAD_FOLDER"], "uploads/products")


def save_blog_image(file_storage) -> str:
    """Lưu ảnh bài blog, trả về đường dẫn tương đối (vd: uploads/blog/xxx.jpg)."""
    return _save_image(file_storage, current_app.config["BLOG_UPLOAD_FOLDER"], "uploads/blog")


def delete_uploaded_image(image_url: str) -> None:
    """Chỉ xóa file nằm trong thư mục upload (không đụng ảnh thương hiệu có sẵn)."""
    if not image_url or not image_url.startswith("uploads/products/"):
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(image_url))
    try:
        os.remove(path)
    except OSError:
        current_app.logger.warning("Không xóa được file ảnh: %s", image_url)