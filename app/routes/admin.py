"""ADMIN"""
import re

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (BlogPost, Brand, Category, ContactMessage, Order, OrderItem, Product, ProductImage,
                        ProductVariant, User)
from app.models.base import utcnow
from app.models.constants import (CONTACT_STATUSES, CONTACT_STATUS_LABELS, ORDER_STATUSES, ORDER_STATUS_LABELS,
                                  ORDER_TRANSITIONS, PAYMENT_STATUS_LABELS, POST_PUBLISHED, POST_STATUSES,
                                  ROLE_CUSTOMER)
from app.services import BusinessError, dashboard_service, order_service
from app.utils.blog_markup import parse_blog
from app.utils.security import admin_required
from app.utils.uploads import UploadError, delete_uploaded_image, save_blog_image, save_product_image
from app.utils.validators import clean, parse_int, slugify

bp = Blueprint("admin", __name__, url_prefix="/admin")

LOGO_RE = re.compile(r"^(images|uploads)/[A-Za-z0-9_\-./']+$")


@bp.before_request
@admin_required
def _guard():
    """Chốt chặn chung cho toàn blueprint."""
    return None


def _unique_slug(model, base, exclude_id=None):
    slug, n = base, 2
    while True:
        stmt = select(model.id).where(model.slug == slug)
        if exclude_id:
            stmt = stmt.where(model.id != exclude_id)
        if db.session.scalar(stmt) is None:
            return slug
        slug, n = f"{base}-{n}", n + 1


def _page():
    return parse_int(request.args.get("page"), default=1, minimum=1)


def _get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if obj is None:
        abort(404)
    return obj


@bp.route("/")
def dashboard():
    recent = db.session.scalars(select(Order).order_by(Order.created_at.desc()).limit(8)).all()
    return render_template("admin/dashboard.html", stats=dashboard_service.admin_stats(), orders=recent)


# Sản phẩm
def _product_form_errors(product, form):
    errors = []
    name = clean(form.get("name"), 200)
    code = clean(form.get("product_code"), 50).upper()
    price = parse_int(form.get("price"), minimum=0)
    sale_raw = clean(form.get("sale_price"))
    sale = parse_int(sale_raw, minimum=0) if sale_raw else None
    category_id = parse_int(form.get("category_id"))
    brand_id = parse_int(form.get("brand_id")) if form.get("brand_id") else None
    if len(name) < 2:
        errors.append("Tên sản phẩm không được để trống.")
    if not code:
        errors.append("Mã sản phẩm không được để trống.")
    if price is None:
        errors.append("Giá phải là số nguyên không âm.")
    if sale_raw and sale is None:
        errors.append("Giá khuyến mãi không hợp lệ.")
    if price is not None and sale is not None and sale > price:
        errors.append("Giá khuyến mãi không được lớn hơn giá gốc.")
    if db.session.get(Category, category_id or 0) is None:
        errors.append("Vui lòng chọn danh mục.")
    if brand_id and db.session.get(Brand, brand_id) is None:
        errors.append("Thương hiệu không hợp lệ.")
    dup = select(Product.id).where(Product.product_code == code)
    if product.id:
        dup = dup.where(Product.id != product.id)
    if code and db.session.scalar(dup):
        errors.append("Mã sản phẩm đã tồn tại.")
    if errors:
        return errors
    product.name, product.product_code = name, code
    product.slug = _unique_slug(Product, slugify(clean(form.get("slug"), 200) or name), product.id)
    product.price, product.sale_price = price, sale
    product.category_id, product.brand_id = category_id, brand_id
    product.description = clean(form.get("description"), 10000) or None
    product.material = clean(form.get("material"), 255) or None
    product.origin = clean(form.get("origin"), 100) or None
    product.is_active = bool(form.get("is_active"))
    return []


MAX_IMAGES_PER_PRODUCT = 12
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB / ảnh


def _product_form_data(product, form=None):
    """Giá trị hiển thị trong form: lấy từ dữ liệu vừa gửi (khi có lỗi, không bắt nhập lại) hoặc từ sản phẩm."""
    if form is not None:
        return {k: form.get(k, "") for k in ("name", "product_code", "slug", "category_id", "brand_id", "price",
                                              "sale_price", "material", "origin", "description")} | {
            "is_active": bool(form.get("is_active"))}
    return {
        "name": product.name or "", "product_code": product.product_code or "", "slug": product.slug or "",
        "category_id": product.category_id or "", "brand_id": product.brand_id or "",
        "price": int(product.price) if product.price is not None else "",
        "sale_price": int(product.sale_price) if product.sale_price is not None else "",
        "material": product.material or "", "origin": product.origin or "",
        "description": product.description or "", "is_active": bool(product.is_active),
    }


def _product_form_context(product, form=None):
    if form is not None and form.get("variants_managed"):
        ids, sizes = form.getlist("variant_id"), form.getlist("variant_size")
        colors, stocks = form.getlist("variant_color"), form.getlist("variant_stock")
        variants = [{"id": ids[i] if i < len(ids) else "", "size": sizes[i],
                     "color": colors[i] if i < len(colors) else "", "stock": stocks[i] if i < len(stocks) else ""}
                    for i in range(len(sizes))]
    else:
        variants = [{"id": v.id, "size": v.size, "color": v.color, "stock": v.stock_quantity}
                    for v in product.variants]
    images = [{"id": i.id, "url": url_for("static", filename=i.image_url), "primary": i.is_primary}
              for i in product.images]
    return dict(product=product, data=_product_form_data(product, form), variants=variants, images=images,
                had_error=form is not None,
                max_images=MAX_IMAGES_PER_PRODUCT, max_image_mb=MAX_IMAGE_BYTES // (1024 * 1024),
                categories=db.session.scalars(select(Category).order_by(Category.name)).all(),
                brands=db.session.scalars(select(Brand).order_by(Brand.name)).all())


def _collect_variants(product, form):
    """Đọc bảng kích cỡ/tồn kho gửi lên. Trả về (danh sách dòng hợp lệ, danh sách lỗi)."""
    ids, sizes = form.getlist("variant_id"), form.getlist("variant_size")
    colors, stocks = form.getlist("variant_color"), form.getlist("variant_stock")
    code = clean(form.get("product_code"), 50).upper()
    owned = {v.id for v in product.variants} if product.id else set()
    rows, errors, seen = [], [], set()
    for i, raw_size in enumerate(sizes):
        size = clean(raw_size, 20)
        color = clean(colors[i] if i < len(colors) else "", 50)
        stock_raw = clean(stocks[i] if i < len(stocks) else "")
        vid = parse_int(ids[i]) if i < len(ids) and ids[i] else None
        if vid not in owned:
            vid = None
        if not (size or color or stock_raw or vid):
            continue  # dòng trống: bỏ qua
        line = f"Dòng kích cỡ {len(rows) + 1}"
        if not size:
            errors.append(f"{line}: chưa nhập size.")
            continue
        stock = parse_int(stock_raw, minimum=0) if stock_raw else 0  # để trống = 0
        if stock is None:
            errors.append(f"{line} (size {size}): tồn kho phải là số nguyên không âm.")
            continue
        key = (size.upper(), color.lower())
        if key in seen:
            errors.append(f"Size {size}" + (f" / {color}" if color else "") + " bị nhập trùng.")
            continue
        seen.add(key)
        sku = (f"{code}-{size}" + (f"-{slugify(color).upper()}" if color else "")).upper()
        rows.append({"id": vid, "size": size, "color": color, "stock": stock, "sku": sku})
    return rows, errors


def _apply_variants(product, rows):
    existing = {v.id: v for v in product.variants}
    keep = {r["id"] for r in rows if r["id"]}
    removed = [v for vid, v in existing.items() if vid not in keep]
    for v in removed:
        db.session.delete(v)
    if removed:
        db.session.flush()  # xóa trước khi thêm để không đụng ràng buộc (size, màu) khi nhập lại cùng size
    for r in rows:
        if r["id"]:
            v = existing[r["id"]]
            v.size, v.color, v.stock_quantity = r["size"], r["color"], r["stock"]
        else:
            product.variants.append(ProductVariant(size=r["size"], color=r["color"], sku=r["sku"],
                                                   stock_quantity=r["stock"]))


def _sku_conflicts(product, rows):
    """SKU của dòng mới trùng với biến thể của sản phẩm khác."""
    new_skus = [r["sku"] for r in rows if not r["id"]]
    if not new_skus:
        return []
    stmt = select(ProductVariant.sku).where(ProductVariant.sku.in_(new_skus))
    if product.id:
        stmt = stmt.where(ProductVariant.product_id != product.id)
    return [f"Mã SKU {sku} đã tồn tại ở sản phẩm khác (hãy đổi mã sản phẩm hoặc size/màu)."
            for sku in db.session.scalars(stmt).all()]


def _save_new_images(files):
    """Lưu các ảnh mới; lỗi ở bất kỳ ảnh nào thì xóa hết ảnh vừa lưu. Trả về (đường dẫn, lỗi)."""
    saved, errors = [], []
    for f in files:
        f.stream.seek(0, 2)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_IMAGE_BYTES:
            errors.append(f"Ảnh “{f.filename}” lớn hơn {MAX_IMAGE_BYTES // (1024 * 1024)}MB.")
            continue
        try:
            saved.append(save_product_image(f))
        except UploadError as e:
            errors.append(f"Ảnh “{f.filename}”: {e}")
    if errors:
        for path in saved:
            delete_uploaded_image(path)
        return [], errors
    return saved, []


def _apply_images(product, form, new_paths):
    """Giữ/xóa ảnh cũ, thêm ảnh mới, đặt ảnh chính. Trả về danh sách đường dẫn ảnh bị xóa (xóa file sau commit)."""
    existing = {i.id: i for i in product.images}
    keep_ids = [i for i in (parse_int(x) for x in form.getlist("keep_image")) if i in existing]
    removed = []
    for iid, img in existing.items():
        if iid not in keep_ids:
            removed.append(img.image_url)
            product.images.remove(img)
    ordered = [existing[i] for i in dict.fromkeys(keep_ids)]
    for path in new_paths:
        img = ProductImage(image_url=path)
        product.images.append(img)
        ordered.append(img)
    pick = clean(form.get("primary"), 20)
    primary = None
    if pick.startswith("old:"):
        primary = existing.get(parse_int(pick[4:]))
    elif pick.startswith("new:"):
        idx = parse_int(pick[4:], minimum=0)
        if idx is not None and idx < len(new_paths):
            primary = ordered[len(ordered) - len(new_paths) + idx]
    if primary not in ordered:
        primary = ordered[0] if ordered else None
    for n, img in enumerate(ordered):
        img.sort_order = n
        img.is_primary = img is primary
    return removed


def _product_submit(product):
    """Một lần bấm Lưu: thông tin + kích cỡ/tồn kho + hình ảnh. Trả về True nếu đã lưu thành công."""
    form = request.form
    new_files = [f for f in request.files.getlist("images") if f and f.filename]
    errors = _product_form_errors(product, form)
    rows = None
    if form.get("variants_managed"):
        rows, v_errors = _collect_variants(product, form)
        errors += v_errors
        if not errors:
            errors += _sku_conflicts(product, rows)
    if form.get("images_managed"):
        kept = len([i for i in form.getlist("keep_image") if parse_int(i)])
        if kept + len(new_files) > MAX_IMAGES_PER_PRODUCT:
            errors.append(f"Tối đa {MAX_IMAGES_PER_PRODUCT} ảnh cho mỗi sản phẩm.")
    if errors:
        db.session.rollback()
        [flash(e, "error") for e in errors]
        return False
    new_paths = []
    if form.get("images_managed") and new_files:
        new_paths, img_errors = _save_new_images(new_files)
        if img_errors:
            db.session.rollback()
            [flash(e, "error") for e in img_errors]
            return False
    removed_files = []
    try:
        if product.id is None:
            db.session.add(product)
        if rows is not None:
            _apply_variants(product, rows)
        if form.get("images_managed"):
            removed_files = _apply_images(product, form, new_paths)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for path in new_paths:
            delete_uploaded_image(path)
        flash("Không lưu được: mã sản phẩm, đường dẫn hoặc kích cỡ bị trùng.", "error")
        return False
    for path in removed_files:
        delete_uploaded_image(path)
    return True


@bp.route("/products")
def products():
    q = clean(request.args.get("q"), 100)
    stmt = select(Product).options(selectinload(Product.variants), selectinload(Product.category),
                                   selectinload(Product.brand), selectinload(Product.images))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.like(like), Product.product_code.like(like)))
    pagination = db.paginate(stmt.order_by(Product.id.desc()), page=_page(),
                             per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/products.html", pagination=pagination, products=pagination.items, q=q)


def _after_save_redirect(product):
    nxt = request.form.get("after")
    flash("Đã lưu sản phẩm." + ("" if product.variants else " Lưu ý: chưa có kích cỡ nào nên khách chưa thể mua."),
          "success" if product.variants else "warning")
    if nxt == "new":
        return redirect(url_for("admin.product_new"))
    if nxt == "stay":
        return redirect(url_for("admin.product_edit", product_id=product.id))
    return redirect(url_for("admin.products"))


@bp.route("/products/new", methods=["GET", "POST"])
def product_new():
    product = Product(is_active=True)
    if request.method == "POST":
        if _product_submit(product):
            return _after_save_redirect(product)
        return render_template("admin/product_form.html", **_product_form_context(Product(is_active=True), request.form))
    return render_template("admin/product_form.html", **_product_form_context(product))


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    product = _get_or_404(Product, product_id)
    if request.method == "POST":
        if _product_submit(product):
            return _after_save_redirect(product)
        product = _get_or_404(Product, product_id)
        return render_template("admin/product_form.html", **_product_form_context(product, request.form))
    return render_template("admin/product_form.html", **_product_form_context(product))


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    product = _get_or_404(Product, product_id)
    has_orders = db.session.scalar(select(func.count(OrderItem.id)).where(OrderItem.product_id == product.id))
    if has_orders:
        product.is_active = False
        db.session.commit()
        flash("Sản phẩm đã có trong đơn hàng nên không xóa hẳn để bảo toàn lịch sử. Đã chuyển sang ẩn.", "warning")
    else:
        files = [i.image_url for i in product.images]
        db.session.delete(product)
        db.session.commit()
        for f in files:
            delete_uploaded_image(f)
        flash("Đã xóa sản phẩm.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/products/<int:product_id>/images", methods=["POST"])
def image_upload(product_id):
    product = _get_or_404(Product, product_id)
    try:
        path = save_product_image(request.files.get("image"))
    except UploadError as e:
        flash(str(e), "error")
    else:
        db.session.add(ProductImage(product_id=product.id, image_url=path, is_primary=not product.images,
                                    sort_order=len(product.images)))
        db.session.commit()
        flash("Đã tải ảnh lên.", "success")
    return redirect(url_for("admin.product_edit", product_id=product.id))


@bp.route("/images/<int:image_id>/primary", methods=["POST"])
def image_primary(image_id):
    img = _get_or_404(ProductImage, image_id)
    for other in img.product.images:
        other.is_primary = other.id == img.id
    db.session.commit()
    flash("Đã đặt làm ảnh chính.", "success")
    return redirect(url_for("admin.product_edit", product_id=img.product_id))


@bp.route("/images/<int:image_id>/delete", methods=["POST"])
def image_delete(image_id):
    img = _get_or_404(ProductImage, image_id)
    product_id, path, was_primary = img.product_id, img.image_url, img.is_primary
    db.session.delete(img)
    db.session.flush()
    if was_primary:
        nxt = db.session.scalars(select(ProductImage).where(ProductImage.product_id == product_id)
                                 .order_by(ProductImage.sort_order, ProductImage.id)).first()
        if nxt:
            nxt.is_primary = True
    db.session.commit()
    delete_uploaded_image(path)
    flash("Đã xóa ảnh.", "success")
    return redirect(url_for("admin.product_edit", product_id=product_id))


@bp.route("/products/<int:product_id>/variants", methods=["POST"])
def variant_add(product_id):
    product = _get_or_404(Product, product_id)
    size, color = clean(request.form.get("size"), 20), clean(request.form.get("color"), 50)
    stock = parse_int(request.form.get("stock_quantity"), minimum=0)
    if not size or stock is None:
        flash("Cần nhập kích cỡ và tồn kho (số nguyên không âm).", "error")
    else:
        sku = clean(request.form.get("sku"), 80) or f"{product.product_code}-{size}" + (f"-{slugify(color).upper()}" if color else "")
        db.session.add(ProductVariant(product_id=product.id, size=size, color=color, sku=sku.upper(),
                                      stock_quantity=stock))
        try:
            db.session.commit()
            flash("Đã thêm biến thể.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Biến thể (kích cỡ/màu) hoặc SKU đã tồn tại.", "error")
    return redirect(url_for("admin.product_edit", product_id=product.id))


@bp.route("/variants/<int:variant_id>/update", methods=["POST"])
def variant_update(variant_id):
    v = _get_or_404(ProductVariant, variant_id)
    stock = parse_int(request.form.get("stock_quantity"), minimum=0)
    if stock is None:
        flash("Tồn kho phải là số nguyên không âm.", "error")
    else:
        v.stock_quantity = stock
        db.session.commit()
        flash("Đã cập nhật tồn kho.", "success")
    return redirect(url_for("admin.product_edit", product_id=v.product_id))


@bp.route("/variants/<int:variant_id>/delete", methods=["POST"])
def variant_delete(variant_id):
    v = _get_or_404(ProductVariant, variant_id)
    pid = v.product_id
    db.session.delete(v)
    db.session.commit()
    flash("Đã xóa biến thể.", "success")
    return redirect(url_for("admin.product_edit", product_id=pid))


# ------------------------------------------------- Danh mục & Thương hiệu
def _simple_list(model, template, endpoint_key):
    items = db.session.scalars(select(model).order_by(model.id)).all()
    counts = dict(db.session.execute(
        select(Product.category_id if model is Category else Product.brand_id, func.count(Product.id))
        .group_by(Product.category_id if model is Category else Product.brand_id)).all())
    edit = _get_or_404(model, parse_int(request.args.get("edit"), default=0)) if request.args.get("edit") else None
    return render_template(template, items=items, counts=counts, edit=edit)


def _simple_save(model, label, list_endpoint, is_brand):
    obj_id = parse_int(request.form.get("id"))
    obj = _get_or_404(model, obj_id) if obj_id else model()
    name = clean(request.form.get("name"), 100)
    if len(name) < 2:
        flash(f"Tên {label} không được để trống.", "error")
        return redirect(url_for(list_endpoint))
    obj.name = name
    obj.slug = _unique_slug(model, slugify(clean(request.form.get("slug"), 120) or name), obj.id)
    obj.description = clean(request.form.get("description"), 2000) or None
    if is_brand:
        logo = clean(request.form.get("logo"), 255)
        if logo and (not LOGO_RE.match(logo) or ".." in logo):
            flash("Đường dẫn logo không hợp lệ (ví dụ: images/logo-tuan.png).", "error")
            return redirect(url_for(list_endpoint))
        obj.logo = logo or None
        cover = clean(request.form.get("cover_image"), 255)
        if cover and (not LOGO_RE.match(cover) or ".." in cover):
            flash("Đường dẫn ảnh đại diện không hợp lệ (ví dụ: images/kodoss.jpg).", "error")
            return redirect(url_for(list_endpoint))
        obj.cover_image = cover or None
    else:
        obj.is_active = bool(request.form.get("is_active"))
    if not obj.id:
        db.session.add(obj)
    try:
        db.session.commit()
        flash(f"Đã lưu {label}.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"Tên hoặc đường dẫn {label} đã tồn tại.", "error")
    return redirect(url_for(list_endpoint))


def _simple_delete(model, obj_id, label, list_endpoint):
    obj = _get_or_404(model, obj_id)
    if obj.products:
        flash(f"Không thể xóa {label} đang có sản phẩm. Hãy chuyển hoặc xóa sản phẩm trước.", "error")
    else:
        db.session.delete(obj)
        db.session.commit()
        flash(f"Đã xóa {label}.", "success")
    return redirect(url_for(list_endpoint))


@bp.route("/categories")
def categories():
    return _simple_list(Category, "admin/categories.html", "category")


@bp.route("/categories/save", methods=["POST"])
def category_save():
    return _simple_save(Category, "danh mục", "admin.categories", False)


@bp.route("/categories/<int:obj_id>/delete", methods=["POST"])
def category_delete(obj_id):
    return _simple_delete(Category, obj_id, "danh mục", "admin.categories")


@bp.route("/brands")
def brands():
    return _simple_list(Brand, "admin/brands.html", "brand")


@bp.route("/brands/save", methods=["POST"])
def brand_save():
    return _simple_save(Brand, "thương hiệu", "admin.brands", True)


@bp.route("/brands/<int:obj_id>/delete", methods=["POST"])
def brand_delete(obj_id):
    return _simple_delete(Brand, obj_id, "thương hiệu", "admin.brands")


# ---------------------------------------------------------------- Khách hàng
@bp.route("/customers")
def customers():
    q = clean(request.args.get("q"), 100)
    stmt = select(User).where(User.role == ROLE_CUSTOMER)
    if q:
        stmt = stmt.where(or_(User.email.like(f"%{q}%"), User.full_name.like(f"%{q}%")))
    pagination = db.paginate(stmt.order_by(User.id.desc()), page=_page(),
                             per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    order_counts = dict(db.session.execute(select(Order.user_id, func.count(Order.id)).group_by(Order.user_id)).all())
    return render_template("admin/customers.html", pagination=pagination, customers=pagination.items,
                           order_counts=order_counts, q=q)


@bp.route("/customers/<int:user_id>/toggle", methods=["POST"])
def customer_toggle(user_id):
    user = _get_or_404(User, user_id)
    if user.id == current_user.id or user.role != ROLE_CUSTOMER:
        flash("Không thể khóa tài khoản này.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash("Đã mở khóa tài khoản." if user.is_active else "Đã khóa tài khoản.", "success")
    return redirect(request.referrer or url_for("admin.customers"))


# ------------------------------------------------------------------ Đơn hàng
@bp.route("/orders")
def orders():
    status = clean(request.args.get("status"), 20).upper()
    q = clean(request.args.get("q"), 50)
    stmt = select(Order).options(selectinload(Order.user))
    if status in ORDER_STATUSES:
        stmt = stmt.where(Order.order_status == status)
    else:
        status = ""
    if q:
        stmt = stmt.where(or_(Order.order_code.like(f"%{q}%"), Order.ship_name.like(f"%{q}%"),
                              Order.ship_phone.like(f"%{q}%")))
    pagination = db.paginate(stmt.order_by(Order.created_at.desc(), Order.id.desc()), page=_page(),
                             per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/orders.html", pagination=pagination, orders=pagination.items, status=status, q=q)


def _order_or_404(code):
    order = db.session.scalar(select(Order).where(Order.order_code == code)
                              .options(selectinload(Order.items), selectinload(Order.payments),
                                       selectinload(Order.user)))
    if order is None:
        abort(404)
    return order


@bp.route("/orders/<order_code>")
def order_detail(order_code):
    order = _order_or_404(order_code)
    return render_template("admin/order_detail.html", order=order,
                           next_statuses=ORDER_TRANSITIONS.get(order.order_status, ()),
                           payment_labels=PAYMENT_STATUS_LABELS)


@bp.route("/orders/<order_code>/status", methods=["POST"])
def order_status(order_code):
    order = _order_or_404(order_code)
    try:
        order_service.admin_update_status(order, clean(request.form.get("status"), 20).upper())
        flash("Đã cập nhật trạng thái đơn hàng.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.order_detail", order_code=order_code))


@bp.route("/orders/<order_code>/payment", methods=["POST"])
def order_payment(order_code):
    order = _order_or_404(order_code)
    try:
        order_service.admin_update_payment(order, clean(request.form.get("payment_status"), 20).upper(),
                                           request.form.get("verification_note"),
                                           request.form.get("transaction_code"))
        flash("Đã cập nhật trạng thái thanh toán.", "success")
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.order_detail", order_code=order_code))


# ---------------------------------------------------------------------- Blog
@bp.route("/blog")
def blog():
    posts = db.session.scalars(select(BlogPost).order_by(BlogPost.created_at.desc())).all()
    return render_template("admin/blog.html", posts=posts)


def _blog_save(post):
    title, content = clean(request.form.get("title"), 200), clean(request.form.get("content"), 100000)
    status = request.form.get("status")
    if len(title) < 3 or len(content) < 10 or status not in POST_STATUSES:
        flash("Cần nhập tiêu đề, nội dung và trạng thái hợp lệ.", "error")
        return False
    post.title, post.content = title, content
    post.slug = _unique_slug(BlogPost, slugify(clean(request.form.get("slug"), 200) or title), post.id)
    post.summary = clean(request.form.get("summary"), 500) or None
    thumb = clean(request.form.get("thumbnail"), 255)
    if thumb and (not LOGO_RE.match(thumb) or ".." in thumb):
        flash("Đường dẫn ảnh đại diện không hợp lệ (ví dụ: images/tuan1.jpg).", "error")
        return False
    post.thumbnail = thumb or None
    post.status = status
    if status == POST_PUBLISHED and not post.published_at:
        post.published_at = utcnow()
    if status != POST_PUBLISHED:
        post.published_at = None
    return True


def _warm_blog_translation(post):
    """Bài đã đăng: dịch sẵn sang en/zh ở nền để khách mở là thấy ngay bản dịch."""
    if post.status == POST_PUBLISHED:
        from app import auto_translate
        auto_translate.warm_blog(current_app._get_current_object(), post.slug)


def _form_sections(post):
    """Các mục để dựng lại form: ưu tiên nội dung admin vừa gửi (khi lưu lỗi), nếu không thì nội dung đã lưu."""
    raw = request.form.get("content") if request.method == "POST" else None
    return parse_blog(raw if raw is not None else (post.content or ""), alternate=False)


@bp.route("/blog/upload-image", methods=["POST"])
def blog_upload_image():
    """Tải 1 ảnh cho bài blog (gọi bằng fetch từ form soạn bài), trả về JSON."""
    try:
        path = save_blog_image(request.files.get("image"))
    except UploadError as e:
        return jsonify(error=str(e)), 400
    return jsonify(path=path, url=url_for("static", filename=path))


@bp.route("/blog/new", methods=["GET", "POST"])
def blog_new():
    post = BlogPost()
    if request.method == "POST" and _blog_save(post):
        db.session.add(post)
        db.session.commit()
        _warm_blog_translation(post)
        flash("Đã tạo bài viết.", "success")
        return redirect(url_for("admin.blog"))
    return render_template("admin/blog_form.html", post=post, sections=_form_sections(post))


@bp.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
def blog_edit(post_id):
    post = _get_or_404(BlogPost, post_id)
    if request.method == "POST":
        if _blog_save(post):
            db.session.commit()
            _warm_blog_translation(post)
            flash("Đã cập nhật bài viết.", "success")
            return redirect(url_for("admin.blog"))
        db.session.rollback()
        post = _get_or_404(BlogPost, post_id)
    return render_template("admin/blog_form.html", post=post, sections=_form_sections(post))


@bp.route("/blog/<int:post_id>/delete", methods=["POST"])
def blog_delete(post_id):
    db.session.delete(_get_or_404(BlogPost, post_id))
    db.session.commit()
    flash("Đã xóa bài viết.", "success")
    return redirect(url_for("admin.blog"))


# ------------------------------------------------------------------- Liên hệ
@bp.route("/contacts")
def contacts():
    status = clean(request.args.get("status"), 20).upper()
    stmt = select(ContactMessage)
    if status in CONTACT_STATUSES:
        stmt = stmt.where(ContactMessage.status == status)
    else:
        status = ""
    pagination = db.paginate(stmt.order_by(ContactMessage.created_at.desc()), page=_page(),
                             per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)
    return render_template("admin/contacts.html", pagination=pagination, messages=pagination.items, status=status,
                           statuses=CONTACT_STATUS_LABELS)


@bp.route("/contacts/<int:msg_id>/status", methods=["POST"])
def contact_status(msg_id):
    msg = _get_or_404(ContactMessage, msg_id)
    new = clean(request.form.get("status"), 20).upper()
    if new not in CONTACT_STATUSES:
        flash("Trạng thái không hợp lệ.", "error")
    else:
        msg.status = new
        db.session.commit()
        flash("Đã cập nhật trạng thái tin nhắn.", "success")
    return redirect(request.referrer or url_for("admin.contacts"))