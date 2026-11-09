"""Giỏ hàng và checkout; giỏ khách vãng lai được lưu trong session phía máy chủ."""
import secrets
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import select, update as sa_update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Cart, CartItem, Order, OrderItem, Payment, ProductVariant
from app.models.base import utcnow
from app.models.constants import ORDER_PENDING, PAYMENT_UNPAID
from app.services import BusinessError, cart_service
from app.utils.validators import clean, normalize_phone, valid_phone

bp = Blueprint("cart", __name__, url_prefix="/cart")
api_orders_bp = Blueprint("api_orders", __name__, url_prefix="/api/orders")


def _guest_cart():
    return session.setdefault("guest_cart", [])


@bp.route("/")
def view_cart():
    if current_user.is_authenticated:
        cart = cart_service.get_cart(current_user)
        summary = cart_service.summarize(cart)
        return render_template("shop/cart.html", cart=cart, summary=summary)
    # Khách chưa đăng nhập vẫn được xem giỏ. Chuẩn hóa session cart thành cùng cấu trúc mà template cần.
    from types import SimpleNamespace
    lines, subtotal, problems = [], Decimal(0), []
    for entry in _guest_cart():
        variant = db.session.get(ProductVariant, entry.get("variant_id"))
        if not variant or not variant.product.is_active:
            continue
        qty = max(1, min(int(entry.get("quantity", 1)), current_app.config["MAX_QTY_PER_ITEM"]))
        unit = variant.product.current_price
        line_total = unit * qty
        subtotal += line_total
        item = SimpleNamespace(id=variant.id, quantity=qty)
        lines.append({"item": item, "variant": variant, "product": variant.product,
                      "unit_price": unit, "line_total": line_total, "issue": None})
    shipping = cart_service.shipping_fee_for(subtotal)
    summary = {"lines": lines, "subtotal": subtotal, "shipping_fee": shipping, "discount": Decimal(0),
               "total": subtotal + shipping, "problems": problems, "count": sum(x["item"].quantity for x in lines)}
    return render_template("shop/cart.html", cart=None, summary=summary)


@bp.route("/add", methods=["POST"])
def add():
    variant_id = request.form.get("variant_id", type=int)
    quantity = request.form.get("quantity", default=1, type=int)
    if current_user.is_authenticated:
        try:
            cart_service.add_item(current_user, variant_id, quantity)
            flash("Đã thêm sản phẩm vào giỏ hàng.", "success")
            if request.form.get("buy_now"):
                return redirect(url_for("cart.checkout"))
        except BusinessError as exc:
            flash(str(exc), "error")
    else:
        variant = db.session.get(ProductVariant, variant_id) if variant_id else None
        if not variant or not variant.product.is_active or quantity < 1 or quantity > current_app.config["MAX_QTY_PER_ITEM"]:
            flash("Sản phẩm hoặc số lượng không hợp lệ.", "error")
        elif quantity > variant.stock_quantity:
            flash("Số lượng vượt quá tồn kho.", "error")
        else:
            entries = _guest_cart()
            entry = next((x for x in entries if x["variant_id"] == variant_id), None)
            new_qty = quantity + (entry["quantity"] if entry else 0)
            if new_qty > min(variant.stock_quantity, current_app.config["MAX_QTY_PER_ITEM"]):
                flash("Số lượng vượt quá tồn kho hoặc giới hạn mỗi sản phẩm.", "error")
            elif entry:
                entry["quantity"] = new_qty
            else:
                entries.append({"variant_id": variant_id, "quantity": quantity})
            session.modified = True
    if request.form.get("buy_now"):
        return redirect(url_for("cart.checkout"))
    return redirect(request.referrer or url_for("cart.view_cart"))


@bp.route("/update", methods=["POST"])
def update():
    item_id = request.form.get("item_id", type=int)
    quantity = request.form.get("quantity", type=int)
    try:
        if current_user.is_authenticated:
            cart_service.update_item(current_user, item_id, quantity)
        else:
            entry = next((x for x in _guest_cart() if x["variant_id"] == item_id), None)
            variant = db.session.get(ProductVariant, item_id) if entry else None
            if not entry or not variant or not quantity or quantity > variant.stock_quantity:
                raise BusinessError("Số lượng không hợp lệ hoặc vượt quá tồn kho.")
            entry["quantity"] = quantity
            session.modified = True
    except BusinessError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cart.view_cart"))


@bp.route("/remove", methods=["POST"])
def remove():
    item_id = request.form.get("item_id", type=int)
    try:
        if current_user.is_authenticated:
            cart_service.remove_item(current_user, item_id)
        else:
            session["guest_cart"] = [x for x in _guest_cart() if x["variant_id"] != item_id]
    except BusinessError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cart.view_cart"))


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        if current_user.is_authenticated:
            address_id = request.form.get("address_id", type=int)
            from app.services.order_service import create_order
            try:
                order = create_order(current_user, address_id, request.form.get("payment_method", "COD"),
                                     request.form.get("customer_note"))
                return redirect(url_for("cart.order_success", order_code=order.order_code))
            except BusinessError as exc:
                flash(str(exc), "error")
        else:
            flash("Vui lòng xác nhận thông tin giao hàng bên dưới.", "warning")
            return redirect(url_for("cart.checkout"))
    if current_user.is_authenticated:
        cart = cart_service.get_cart(current_user)
        summary = cart_service.summarize(cart)
    else:
        return render_template("shop/guest_checkout.html", guest_cart=_guest_cart())
    if not summary["lines"]:
        flash("Giỏ hàng đang trống.", "warning")
        return redirect(url_for("cart.view_cart"))
    return render_template("shop/checkout.html", cart=cart, summary=summary)


@bp.route("/guest-checkout", methods=["POST"])
@api_orders_bp.route("/guest-checkout", methods=["POST"])
def guest_checkout():
    data = request.get_json(silent=True) or request.form
    name = clean(data.get("customer_name") or data.get("ship_name"), 120)
    phone = normalize_phone(clean(data.get("customer_phone") or data.get("ship_phone"), 20))
    address = clean(data.get("shipping_address") or data.get("ship_address"), 500)
    note = clean(data.get("order_note") or data.get("customer_note"), 500) or None
    method = clean(data.get("payment_method") or "COD", 20)
    if len(name) < 2 or not valid_phone(phone) or len(address) < 8:
        return jsonify({"error": "Vui lòng kiểm tra họ tên, số điện thoại và địa chỉ nhận hàng."}), 400
    if method not in current_app.config["ENABLED_PAYMENT_METHODS"]:
        return jsonify({"error": "Phương thức thanh toán không được hỗ trợ."}), 400
    ip = request.remote_addr or "unknown"
    if not _guest_cart():
        return jsonify({"error": "Giỏ hàng đang trống."}), 400
    if not current_app.config.get("TESTING", False):
        # Không cho phép gửi đơn hàng hàng loạt từ cùng IP.
        from app.services import rate_limit_service
        if rate_limit_service.is_blocked("guest_order_ip", ip, current_app.config.get("GUEST_ORDER_MAX_PER_IP_HOUR", 20), 3600):
            return jsonify({"error": "Bạn đặt hàng quá nhanh. Vui lòng thử lại sau."}), 429
        if rate_limit_service.is_blocked("guest_order_phone", phone, current_app.config.get("GUEST_ORDER_MAX_PER_PHONE_HOUR", 5), 3600):
            return jsonify({"error": "Số điện thoại đã đặt nhiều đơn trong thời gian ngắn."}), 429
    try:
        subtotal = Decimal(0)
        items = []
        for entry in sorted(_guest_cart(), key=lambda x: x["variant_id"]):
            variant_id, qty = int(entry["variant_id"]), int(entry["quantity"])
            variant = db.session.scalar(select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update())
            if not variant or not variant.product.is_active or qty < 1 or qty > variant.stock_quantity:
                raise BusinessError("Một sản phẩm đã hết hàng hoặc thay đổi tồn kho. Vui lòng kiểm tra giỏ hàng.")
            price = Decimal(variant.product.current_price)
            result = db.session.execute(sa_update(ProductVariant).where(
                ProductVariant.id == variant.id, ProductVariant.stock_quantity >= qty
            ).values(stock_quantity=ProductVariant.stock_quantity - qty))
            if result.rowcount != 1:
                raise BusinessError("Tồn kho vừa thay đổi. Vui lòng thử lại.")
            line_total = price * qty
            subtotal += line_total
            items.append(OrderItem(product_variant_id=variant.id, product_id=variant.product.id,
                product_name=variant.product.name, product_code=variant.product.product_code,
                size=variant.size, color=variant.color, unit_price=price, quantity=qty, subtotal=line_total))
        shipping = cart_service.shipping_fee_for(subtotal)
        total = subtotal + shipping
        code = "GT" + secrets.token_hex(6).upper()
        order = Order(order_code=code, user_id=None, address_id=None, ship_name=name, ship_phone=phone,
            ship_address=address, subtotal=subtotal, shipping_fee=shipping, discount_amount=Decimal(0),
            total_amount=total, payment_method=method, payment_status=PAYMENT_UNPAID,
            order_status=ORDER_PENDING, customer_note=note)
        order.items = items
        order.payments.append(Payment(payment_method=method, amount=total, payment_status=PAYMENT_UNPAID))
        db.session.add(order)
        db.session.flush()
        from app.services import rate_limit_service
        rate_limit_service.record("guest_order_ip", ip)
        rate_limit_service.record("guest_order_phone", phone)
        db.session.commit()
        session.pop("guest_cart", None)
        session["last_guest_order"] = {"code": code, "phone_hash": secrets.token_hex(16)}
        if request.is_json:
            return jsonify({"message": "Đặt hàng thành công.", "order_code": code,
                            "redirect_url": url_for("cart.order_success", order_code=code)}), 201
        return redirect(url_for("cart.order_success", order_code=code))
    except BusinessError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Guest checkout thất bại")
        return jsonify({"error": "Không thể tạo đơn hàng lúc này. Giỏ hàng vẫn được giữ."}), 500


@bp.route("/order-success/<order_code>")
def order_success(order_code):

    if session.get("last_guest_order", {}).get("code") != order_code and not current_user.is_authenticated:
        abort(404)
    from app.models import Order
    order = db.session.scalar(select(Order).where(Order.order_code == order_code).options(selectinload(Order.items)))
    if order is None or (order.user_id is not None and (not current_user.is_authenticated or order.user_id != current_user.id)):
        abort(404)
    return render_template("shop/order_success.html", order=order)