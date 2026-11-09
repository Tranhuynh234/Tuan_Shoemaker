"""Chuyển ngôn ngữ Việt / Anh / Trung cho các trang phía khách hàng.

Cách hoạt động: ngôn ngữ lưu trong cookie `lang` (vi|en|zh). Khi khác `vi`, HTML trả về được dịch
theo từ điển (TEXT cho tiếng Anh, app/i18n_zh.py cho tiếng Trung) (khớp nguyên văn từng đoạn chữ + một số mẫu có số liệu động).
- Muốn thêm/sửa bản dịch: thêm cặp "tiếng Việt": "English" vào TEXT, rồi thêm "English": "中文" vào i18n_zh.py.
- Nội dung do admin nhập (tên sản phẩm, bài blog...) không dịch.
- Trang quản trị luôn giữ tiếng Việt.
"""
import html as _html
import re

from . import auto_translate
from .i18n_extra import ROWS as _EXTRA_ROWS, TAIL_PATTERNS as _TAIL_PATTERNS, ZH_ONLY as _ZH_ONLY
from .i18n_zh import ZH_BY_EN, ZH_EXTRA, ZH_PATTERNS

LANGS = ("vi", "en", "zh")
DEFAULT_LANG = "vi"

TEXT = {
    # ---- Điều hướng / chung
    "SÁNG / TỐI": "LIGHT / DARK", "sáng/tối": "light/dark", "NGÔN NGỮ": "LANGUAGE", "Chọn ngôn ngữ": "Choose language", "Lưu": "Save",
    "Tài khoản và cài đặt": "Account and settings",
    "TRANG CHỦ": "HOME", "LIÊN HỆ": "CONTACT", "GIỚI THIỆU": "ABOUT", "ĐĂNG KÝ": "SIGN UP", "ĐĂNG NHẬP": "LOG IN",
    "ĐĂNG XUẤT": "LOG OUT", "SẢN PHẨM": "PRODUCTS", "TÀI KHOẢN": "ACCOUNT", "QUẢN TRỊ": "ADMIN",
    "GIỎ HÀNG": "CART", "Blogs": "Blog", "Đóng": "Close", "Đóng menu": "Close menu",
    "Tất cả sản phẩm": "All products", "Giày nam": "Men's shoes", "Giày nữ": "Women's shoes",
    "Giày thể thao": "Sports shoes", "Phụ kiện": "Accessories",
    "LIÊN HỆ CHÚNG TÔI": "CONTACT US", "Giới thiệu": "About", "Liên hệ": "Contact",
    "Đăng ký": "Sign up", "Đăng nhập": "Log in", "Đăng xuất": "Log out", "Về trang chủ": "Back to home",
    "Chuyển sang tiếng Anh": "Switch to English", "Chuyển sang tiếng Việt": "Switch to Vietnamese",
    "Chế độ sáng/tối": "Toggle light/dark mode", "Thương hiệu": "Brand", "Danh mục": "Category",
    "282A Hoà Bình, Phường Phú Thạnh, Thành phố Hồ Chí Minh": "282A Hoa Binh, Phu Thanh Ward, Ho Chi Minh City",
    "Monday - Sunday (9:00 am Mở cửa - 9:00 pm Đóng cửa)": "Monday - Sunday (open 9:00 am - close 9:00 pm)",
    "Thứ Hai - Chủ Nhật (9:00 Mở cửa - 21:00 Đóng cửa)": "Monday - Sunday (open 9:00 am - close 9:00 pm)",
    "282A Hòa Bình, Phường Phú Thạnh, Thành phố Hồ Chí Minh": "282A Hoa Binh, Phu Thanh Ward, Ho Chi Minh City",
    "KẾT NỐI VỚI CHÚNG TÔI": "FOLLOW US",
    "TẢI ỨNG DỤNG": "GET THE APP",
    # ---- Trang chủ / giới thiệu
    "DỊCH VỤ CỦA GIÀY TUẤN": "GIÀY TUẤN SERVICES", "GIAO HÀNG TOÀN QUỐC": "NATIONWIDE DELIVERY",
    "Giao hàng trên toàn quốc, áp dụng cho mọi đơn hàng": "Nationwide delivery on every order",
    "CHĂM SÓC &amp; SỬA GIÀY": "SHOE CARE &amp; REPAIR",
    "Gia công sắc sảo tỉ mỉ từng chi tiết, chất lượng da thật": "Sharp, meticulous craftsmanship in every detail, genuine leather quality",
    "NHẬN HÀNG TẠI CỬA HÀNG": "COLLECT IN STORE", "Đặt hàng online và nhận trực tiếp tại cửa hàng": "Order online and collect directly in store",
    "Xem chi tiết": "View details",
    "CỬA HÀNG CỦA CHÚNG TÔI": "OUR STORE",
    "Bản đồ cửa hàng": "Store map",
    "Chỉ đường": "Get directions",
    "282A Hòa Bình, phường Phú Thạnh, thành phố Hồ Chí Minh": "282A Hoa Binh, Phu Thanh Ward, Ho Chi Minh City",
    "KHÁM PHÁ NGAY": "DISCOVER NOW", "THƯƠNG HIỆU": "BRANDS", "TUẤN Hero Banner": "TUẤN hero banner",
    "Chưa có thương hiệu nào. Hãy chạy lệnh seed hoặc thêm trong trang quản trị.": "No brands yet.",
    "Giày Tây luôn là người bạn đồng hành bền bỉ của các quý ông công sở qua bao tháng ngày":
        "Dress shoes have always been the lasting companion of office gentlemen through the years.",
    "Thoải mái, tự tin sải bước cùng giày tây Oxford - Nâng tầm phong thái và đẳng cấp quý ông":
        "Walk with comfort and confidence in Oxford shoes - elevating a gentleman's style and class.",
    "Năng động mỗi ngày, sẵn sàng chinh phục mọi thử thách": "Active every day, ready to take on every challenge.",
    "Di sản cố đô": "Imperial city heritage", "Thủ công": "Handcrafted", "Hiện đại": "Modern",
    "Khởi nguồn từ năm 1978 tại phố Mai Thúc Loan, Huế. Giữa nhịp sống vội vã, chúng tôi chọn cách làm chậm lại một chút để từng đường kim, góc bo được vuông vức, êm ái nhất.":
        "Born in 1978 on Mai Thuc Loan street, Hue. In a hurried world, we choose to slow down so every stitch and every curve is as neat and comfortable as it can be.",
    "Khám phá": "Explore", "Bộ sưu tập": "Collections", "Di Sản Cố Đô – Nâng Tầm Bước Chân Hiện Đại":
        "Imperial Heritage – Elevating Modern Steps",
    "Giày Tuấn kết hợp tinh thần thủ công truyền thống với ngôn ngữ hiện đại, tạo nên từng bước chân lịch lãm, sang trọng và bền bỉ.":
        "Giày Tuấn blends traditional craftsmanship with a modern language for steps that are elegant, refined and durable.",
    "Xem câu chuyện": "Read our story",
    "Từng đường kim được hoàn thiện bởi bàn tay người thợ xứ Huế.": "Every stitch is finished by the hands of Hue artisans.",
    "Phong cách quý ông tinh tế, phù hợp với cuộc sống thành thị.": "A refined gentleman's style for city life.",
    "Chậm lại để bền vững hơn": "Slowing down to last longer",
    "Tiền thân của Công ty TNHH Sản Xuất Thương Mại Dịch Vụ Đăng Tuấn là \"Hiệu Giày Tuấn\" do ông Nguyễn Đăng Tuấn sáng lập vào năm 1978 tại số 95 cũ nay là số 109 Mai Thúc Loan, Thành phố Huế.":
        "The predecessor of Dang Tuan Production Trading Service Co., Ltd. is \"Hieu Giay Tuan\", founded by Mr. Nguyen Dang Tuan in 1978 at the former No. 95, now No. 109 Mai Thuc Loan, Hue City.",
    "Chúng tôi chọn cách làm chậm lại một chút để từng đường kim, góc bo được vuông vức, êm ái nhất. Máy móc tối ưu quy trình, nhưng đôi bàn tay người thợ xứ Huế mới là yếu tố tạo nên cái hồn và sự bền bỉ qua năm tháng.":
        "We choose to slow down so every stitch and curve is as neat and comfortable as it can be. Machines optimise the process, but the hands of Hue artisans give each pair its soul and lasting durability.",
    "Xem sản phẩm": "View products", "Di sản thủ công": "Handcrafted heritage",
    "TÂM HUYẾT NGHỆ NHÂN": "ARTISANS' DEDICATION", "BỘ SƯU TẬP": "COLLECTION",
    "Từng đường kim mũi chỉ được chăm chút tỉ mỉ từ bàn tay người thợ.": "Every stitch is carefully tended by the artisan's hands.",
    "Giày Tây Nam Cổ Điển": "Classic Men's Dress Shoes", "Giày Nữ": "Women's Shoes", "Phụ Kiện": "Accessories",
    "DÒNG SẢN PHẨM": "PRODUCT LINE", "Sneaker &amp; Thể Thao Năng Động": "Sneakers &amp; Active Sports",
    "PHIÊN BẢN": "EDITION", "LƯU GIỮ DI SẢN": "PRESERVING HERITAGE",
    "Giữ trọn hồn cốt xứ Huế qua từng thế hệ làm giày truyền thống.": "Keeping the soul of Hue alive through generations of traditional shoemaking.",
    "Dấu ấn &amp; Niềm tin": "Signature &amp; Trust", "Trải nghiệm vượt mong đợi": "An experience beyond expectations",
    "Chế tác bằng trái tim": "Crafted with heart",
    "Chúng tôi chọn cách làm chậm lại một chút để từng đường kim, góc bo được vuông vức, êm ái nhất. Máy móc tối ưu quy trình, nhưng đôi bàn tay người thợ xứ Huế mới là yếu tố tạo nên cái hồn.":
        "We choose to slow down so every stitch and curve is as neat and comfortable as it can be. Machines optimise the process, but the hands of Hue artisans give each pair its soul.",
    "Dịch vụ tận tâm": "Dedicated service",
    "Bạn không cần phải lo lắng khi muốn kiểm tra đơn hàng. Chúng tôi luôn sẵn sàng trả lời mọi câu hỏi của bạn. Chỉ cần nhấp vào biểu tượng chat và chúng tôi sẽ trò chuyện.":
        "No need to worry when you want to check an order. We are always ready to answer every question. Just click the chat icon and we will talk.",
    "Hậu mãi chuẩn mực": "Exemplary after-sales care",
    "Hoàn trả là một trải nghiệm không mong muốn, nhưng khi nó xảy ra, chúng tôi sẽ đảm bảo bạn trải qua quy trình mượt mà và thân thiện.":
        "Returns are an unwanted experience, but when they happen we will make sure the process is smooth and friendly.",
    "Chúng tôi theo đuổi những đôi giày được làm cẩn thận, bền bỉ và thanh lịch cho quý ông hiện đại, từ Classic công sở, Modern lịch lãm đến Sport năng động.":
        "We pursue carefully made, durable and elegant shoes for the modern gentleman, from office Classic and refined Modern to active Sport.",
    "Các thương hiệu tại cửa hàng:": "Brands in our store:", "và": "and", "Liên hệ với chúng tôi": "Contact us",
    "Địa chỉ: 282A Hoà Bình, Phường Phú Thạnh, Thành phố Hồ Chí Minh · Điện thoại: +84 91 977 22 55 · Mở cửa 9:00 – 21:00 mỗi ngày.":
        "Address: 282A Hoa Binh, Phu Thanh Ward, Ho Chi Minh City · Phone: +84 91 977 22 55 · Open 9:00 – 21:00 every day.",
    # ---- Danh sách / chi tiết sản phẩm
    "Tìm theo tên hoặc mã sản phẩm...": "Search by name or product code...", "Tìm kiếm": "Search",
    "Tất cả danh mục": "All categories", "Tất cả thương hiệu": "All brands", "Lọc": "Filter", "Xóa lọc": "Clear filters",
    "Sản phẩm": "Products", "Mới nhất": "Newest", "Giá: thấp đến cao": "Price: low to high",
    "Giá: cao đến thấp": "Price: high to low", "Sắp xếp": "Sort", "Giá từ": "Price from", "Giá đến": "Price to",
    "Giá từ (₫)": "Price from (₫)", "Giá đến (₫)": "Price to (₫)",
    "Không tìm thấy sản phẩm phù hợp.": "No matching products found.", "Xem tất cả sản phẩm": "View all products",
    "Phân trang": "Pagination", "Chưa có ảnh": "No image", "Chưa có ảnh sản phẩm": "No product image",
    "SẢN PHẨM ĐÃ XEM GẦN ĐÂY": "RECENTLY VIEWED", "Xóa lịch sử": "Clear history",
    "Xóa lịch sử đã xem?": "Clear your viewing history?", "THÔNG TIN SẢN PHẨM": "PRODUCT INFORMATION",
    "Chọn kích cỡ / màu": "Choose size / colour", "Chọn kích cỡ": "Choose size", "Số lượng": "Quantity",
    "Thêm vào giỏ hàng": "Add to cart", "Mua ngay": "Buy now", "Hết hàng": "Out of stock", "Còn hàng": "In stock",
    "Sản phẩm hiện đã hết hàng hoặc chưa mở bán.": "This product is out of stock or not yet on sale.",
    "ĐÁNH GIÁ SẢN PHẨM": "PRODUCT REVIEWS", "Chưa có đánh giá nào.": "No reviews yet.",
    "Viết đánh giá của bạn": "Write your review", "Điểm": "Rating", "Nhận xét": "Comment", "Gửi đánh giá": "Submit review",
    "SẢN PHẨM LIÊN QUAN": "RELATED PRODUCTS", "Đang xử lý...": "Processing...",
    # ---- Giỏ hàng / thanh toán
    "Giỏ hàng của bạn đang trống.": "Your cart is empty.", "Khám phá sản phẩm": "Explore products",
    "Cập nhật": "Update", "Xóa": "Delete", "Tóm tắt đơn hàng": "Order summary", "Tạm tính": "Subtotal",
    "Phí giao hàng": "Shipping fee", "Miễn phí": "Free", "Tổng cộng": "Total", "Giảm giá": "Discount",
    "Tiến hành đặt hàng": "Proceed to checkout", "Tiếp tục mua sắm": "Continue shopping",
    "Vui lòng điều chỉnh các sản phẩm có cảnh báo trước khi thanh toán.": "Please fix the items with warnings before checking out.",
    "Xóa sản phẩm này khỏi giỏ hàng?": "Remove this item from your cart?", "Số lượng ": "Quantity ",
    "ĐẶT HÀNG": "CHECKOUT", "Địa chỉ giao hàng": "Delivery address", "Bạn chưa có địa chỉ nhận hàng.": "You have no delivery address yet.",
    "+ Thêm địa chỉ mới": "+ Add new address", "Phương thức thanh toán": "Payment method",
    "Thanh toán khi nhận hàng (COD)": "Cash on delivery (COD)", "Thanh toán trực tuyến chưa được tích hợp.": "Online payment is not available yet.",
    "Ghi chú cho đơn hàng": "Order note", "Đơn hàng của bạn": "Your order", "Xác nhận đặt hàng": "Place order",
    "Giỏ hàng có sản phẩm không đủ hàng.": "Some items in your cart are out of stock.", "Quay lại giỏ hàng": "Back to cart",
    "Vui lòng thêm địa chỉ giao hàng.": "Please add a delivery address.",
    "Giá và tổng tiền được tính lại bởi hệ thống khi đặt hàng.": "Prices and totals are recalculated by the system when you order.",
    "Đang đặt hàng...": "Placing order...", "Đặt hàng thành công": "Order placed successfully",
    "Mã đơn hàng của bạn:": "Your order code:", "Xem đơn hàng": "View order",
    # ---- Đăng nhập / đăng ký / liên hệ
    "Mật khẩu": "Password", "Mật khẩu *": "Password *", "Ghi nhớ đăng nhập": "Remember me",
    "Chưa có tài khoản?": "Don't have an account?", "Đã có tài khoản?": "Already have an account?",
    "Họ và tên": "Full name", "Họ và tên *": "Full name *", "Số điện thoại": "Phone number", "Số điện thoại *": "Phone number *",
    "(tối thiểu 8 ký tự, gồm chữ và số)": "(at least 8 characters, letters and numbers)",
    "Xác nhận mật khẩu *": "Confirm password *", "Tạo tài khoản": "Create account", "Đang tạo tài khoản...": "Creating account...",
    "Đang đăng nhập...": "Logging in...", "Tiêu đề *": "Subject *", "Nội dung *": "Message *", "Gửi tin nhắn": "Send message",
    "Đang gửi...": "Sending...",
    # ---- Tài khoản
    "Cài đặt": "Settings", "Đơn mua": "My orders", "Đang giao": "Shipping", "Lịch sử mua hàng": "Purchase history",
    "Địa chỉ nhận hàng": "Delivery addresses", "Tổng đơn hàng": "Total orders", "Đang xử lý": "Processing",
    "Hoàn thành": "Completed", "Đơn hàng gần đây": "Recent orders", "Mã đơn": "Order code", "Ngày đặt": "Order date",
    "Tổng tiền": "Total", "Trạng thái": "Status", "Chưa có dữ liệu hoạt động": "No activity yet",
    "Tất cả": "All", "Số SP": "Items", "Thanh toán": "Payment", "Không có đơn hàng nào": "No orders",
    "Size/Màu": "Size/Colour", "Đơn giá": "Unit price", "Thành tiền": "Amount", "Sản phẩm ": "Products ",
    "Giao hàng &amp; thanh toán": "Delivery &amp; payment", "Hủy đơn hàng": "Cancel order", "Đang hủy...": "Cancelling...",
    "Thông tin cá nhân": "Personal information", "Lưu thay đổi": "Save changes", "Đang lưu...": "Saving...",
    "Đổi mật khẩu": "Change password", "Mật khẩu hiện tại": "Current password", "Mật khẩu mới": "New password",
    "Xác nhận mật khẩu mới": "Confirm new password", "Đang đổi...": "Changing...", "Bạn chưa có địa chỉ nào.": "You have no addresses yet.",
    "Mặc định": "Default", "Sửa": "Edit", "Xóa địa chỉ này?": "Delete this address?", "Tên người nhận *": "Recipient name *",
    "Tỉnh/Thành phố *": "Province / City *", "Quận/Huyện *": "District *", "Phường/Xã *": "Ward *",
    "Địa chỉ chi tiết (số nhà, tên đường) *": "Street address *", "Đặt làm địa chỉ mặc định": "Set as default address",
    "Lưu địa chỉ": "Save address",
    # ---- Blog / lỗi
    "Chưa có bài viết nào được xuất bản.": "No posts have been published yet.", "Không tìm thấy trang": "Page not found",
    "Trang bạn tìm không tồn tại hoặc đã bị di chuyển.": "The page you are looking for does not exist or has been moved.",
    "Không có quyền truy cập": "Access denied", "Bạn không có quyền thực hiện thao tác này.": "You do not have permission to do this.",
    "Đã xảy ra lỗi": "Something went wrong", "Hệ thống gặp sự cố. Vui lòng thử lại sau.": "The system ran into a problem. Please try again later.",
    "Yêu cầu không hợp lệ": "Invalid request", "Tệp quá lớn": "File too large",
    # ---- Nhãn trạng thái
    "Chờ xác nhận": "Pending confirmation", "Đã xác nhận": "Confirmed", "Đã hủy": "Cancelled",
    "Chưa thanh toán": "Unpaid", "Đã thanh toán": "Paid", "Thất bại": "Failed", "Đã hoàn tiền": "Refunded",
    # ---- Thông báo (flash)
    "Đã thêm sản phẩm vào giỏ hàng.": "Added to your cart.", "Đã cập nhật số lượng.": "Quantity updated.",
    "Đã xóa sản phẩm khỏi giỏ hàng.": "Item removed from your cart.", "Đơn hàng đã được hủy.": "Your order has been cancelled.",
    "Đã cập nhật thông tin cá nhân.": "Personal information updated.", "Đã đổi mật khẩu.": "Password changed.",
    "Đã lưu địa chỉ.": "Address saved.", "Đã xóa địa chỉ.": "Address deleted.", "Bạn đã đăng xuất.": "You have been logged out.",
    "Đăng ký thành công. Chào mừng bạn đến với TUẤN!": "Sign-up successful. Welcome to TUẤN!",
    "Mật khẩu hiện tại không đúng.": "Current password is incorrect.", "Số điện thoại không hợp lệ.": "Invalid phone number.",
    "Số điện thoại người nhận không hợp lệ.": "Invalid recipient phone number.",
    "Vui lòng nhập họ tên.": "Please enter your full name.", "Vui lòng nhập họ tên (tối thiểu 2 ký tự).": "Please enter your full name (at least 2 characters).",
    "Vui lòng nhập tiêu đề (tối thiểu 3 ký tự).": "Please enter a subject (at least 3 characters).",
    "Nội dung tin nhắn quá ngắn (tối thiểu 10 ký tự).": "Your message is too short (at least 10 characters).",
    "Mật khẩu phải có ít nhất 8 ký tự.": "Password must be at least 8 characters.", "Mật khẩu phải gồm cả chữ và số.": "Password must contain letters and numbers.",
    "Vui lòng đăng nhập để tiếp tục.": "Please log in to continue.",
    "Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng.": "Please log in to add items to your cart.",
    "Cảm ơn bạn! Chúng tôi đã nhận được tin nhắn và sẽ phản hồi sớm.": "Thank you! We received your message and will reply soon.",
    "Cảm ơn bạn đã đánh giá sản phẩm.": "Thank you for reviewing this product.",
    "Bạn chỉ có thể đánh giá sản phẩm đã mua và nhận hàng thành công.": "You can only review products you have purchased and received.",
    "Điểm đánh giá phải từ 1 đến 5.": "Rating must be from 1 to 5.",
    "Sản phẩm hoặc kích cỡ không tồn tại hoặc đã ngừng bán.": "This product or size does not exist or is no longer sold.",
    "Số lượng không hợp lệ. Dùng nút xóa để bỏ sản phẩm.": "Invalid quantity. Use the delete button to remove the item.",
    "Không tìm thấy sản phẩm trong giỏ hàng.": "Item not found in your cart.", "Không tìm thấy đơn hàng.": "Order not found.",
    "Chỉ có thể hủy đơn đang ở trạng thái «Chờ xác nhận».": "Only orders in “Pending confirmation” can be cancelled.",
    "Vui lòng chọn địa chỉ giao hàng hợp lệ.": "Please choose a valid delivery address.",
    "Phương thức thanh toán này hiện chưa được hỗ trợ.": "This payment method is not supported yet.",
    "Không thể tạo đơn hàng lúc này. Vui lòng thử lại sau.": "Unable to create the order right now. Please try again later.",
    "Phiên làm việc không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang và thử lại.": "Your session is invalid or expired. Please reload the page and try again.",
    "Phiên làm việc không hợp lệ hoặc dữ liệu gửi lên không đúng. Vui lòng tải lại trang.": "Your session is invalid or the submitted data is wrong. Please reload the page.",
    "Dung lượng tệp vượt quá giới hạn 5 MB.": "The file exceeds the 5 MB limit.",
    "Giỏ hàng của bạn đang trống.": "Your cart is empty.",
}

# Mẫu có số liệu/biến động: (regex, thay thế). Áp dụng lần lượt trên đoạn chữ chưa khớp nguyên văn.
PATTERNS = [
    (r"^Còn (\d+)$", r"Only \1 left"),
    (r"^GIỎ HÀNG \((\d+)\)$", r"CART (\1)"),
    (r"^Xin chào (.+)$", r"Hello \1"),
    (r"Đã bán (\d+)", r"Sold \1"),
    (r"(\d+) đánh giá", r"\1 reviews"),
    (r"^Mã sản phẩm: ", "Product code: "),
    (r"^Chất liệu: ", "• Material: "),
    (r"^Loại sản phẩm: ", "• Category: "),
    (r"^Thương hiệu: ", "• Brand: "),
    (r"^Xuất xứ: ", "• Origin: "),
    (r"^Đơn hàng (GT\w+)$", r"Order \1"),
    (r"^Đặt lúc ", "Placed at "),
    (r"^Ghi chú: ", "Note: "),
    (r"^Giao đến: ", "Deliver to: "),
    (r" · Tổng thanh toán ", " · Total payable "),
    (r"^Thanh toán khi nhận hàng \(COD\)", "Cash on delivery (COD)"),
    (r"^Chỉ còn (\d+) sản phẩm \((.+)\) trong kho\.$", r"Only \1 left in stock (\2)."),
    (r"^Chỉ còn (\d+) sản phẩm trong kho\.$", r"Only \1 left in stock."),
    (r"^Chỉ còn (\d+) trong kho$", r"Only \1 left in stock"),
    (r"^Mỗi sản phẩm tối đa (\d+) cái( trong giỏ)?\.$", r"Maximum \1 per item."),
    (r"^Số lượng phải từ 1 đến (\d+)\.$", r"Quantity must be between 1 and \1."),
    (r"^Sản phẩm «(.+)» hiện không còn bán\. Vui lòng xóa khỏi giỏ\.$", r"“\1” is no longer on sale. Please remove it from your cart."),
    (r"^«(.+)» \((.+)\) không đủ số lượng tồn kho\.$", r"“\1” (\2) does not have enough stock."),
    (r"^(.+) không được để trống\.$", r"\1 is required."),
    (r"^Bạn chắc chắn muốn hủy đơn hàng (\w+)\?$", r"Are you sure you want to cancel order \1?"),
]
_COMPILED = [(re.compile(p), r) for p, r in PATTERNS]

# Tiếng Trung: ghép "tiếng Việt -> tiếng Trung" qua bản tiếng Anh, câu nào thiếu thì giữ tiếng Việt.
TEXT_ZH = {vi: ZH_BY_EN[en] for vi, en in TEXT.items() if en in ZH_BY_EN}
TEXT_ZH.update(ZH_EXTRA)
_COMPILED_ZH = [(re.compile(p), r) for p, r in ZH_PATTERNS]

# Bản dịch bổ sung (app/i18n_extra.py): bản đã có ở trên luôn được ưu tiên.
for _vi, _en, _zh in _EXTRA_ROWS:
    TEXT.setdefault(_vi, _en)
    TEXT_ZH.setdefault(_vi, _zh)
for _k, _v in _ZH_ONLY.items():
    TEXT_ZH.setdefault(_k, _v)
_TAIL = [(re.compile(p), en, zh) for p, en, zh in _TAIL_PATTERNS]

# Tra từ điển không phân biệt hoa/thường (vd. tiêu đề "GIÀY TÂY NAM" hay "tất cả sản phẩm nam").
_LOWER = {"en": {k.lower(): v for k, v in TEXT.items()}, "zh": {k.lower(): v for k, v in TEXT_ZH.items()}}

_DICTS = {"en": (TEXT, _COMPILED), "zh": (TEXT_ZH, _COMPILED_ZH)}

TEXT_NODE = re.compile(r">([^<>]+)<")
ATTR = re.compile(r'\b(placeholder|aria-label|alt|title|data-confirm|data-loading-text|data-default-text|data-error-text|data-label-play|data-label-pause)="([^"]*)"')
HAS_VI = re.compile(r"[À-ỹ]")


def _lookup(piece: str, texts: dict, lang: str) -> str:
    """Dịch một mảnh chữ (vd. tên danh mục) nếu có trong từ điển, không thì giữ nguyên."""
    return texts.get(piece) or _LOWER.get(lang, _LOWER["en"]).get(piece.lower()) or piece


def translate_text(s: str, lang: str = "en") -> str:
    texts, patterns = _DICTS.get(lang, _DICTS["en"])
    key = " ".join(s.split())
    if not key or not HAS_VI.search(key) and key not in texts:
        return s
    if key in texts:
        return texts[key]
    low = _LOWER.get(lang, _LOWER["en"]).get(key.lower())
    if low is not None:  # khác hoa/thường so với khóa trong từ điển
        return low.upper() if lang != "zh" and key.isupper() else low

    for rx, en, zh in _TAIL:  # câu có chỗ trống động (tên danh mục, số liệu...)
        m = rx.match(key)
        if m:
            parts = [_lookup(g, texts, lang) for g in m.groups()]
            return (zh if lang == "zh" else en).format(*parts)

    # tiêu đề trang dạng "<tên trang> - TUẤN ..."
    m = re.match(r"^(.*?)(TUẤN.*| \| .*)$", key)
    if m:
        head = m.group(1)
        base = head.rstrip(" -–|")
        if head in texts:
            return texts[head] + m.group(2)
        if base and base != head and _lookup(base, texts, lang) != base:
            return _lookup(base, texts, lang) + head[len(base):] + m.group(2)

    out = key
    for rx, rep in patterns:
        out = rx.sub(rep, out)
    return out if out != key else s


_BRAND = re.compile(r"Tuấn|TUẤN|Giày|Huế|×")
_CODE = re.compile(r"function\s*\(|=>|document\.|window\.|\bvar\b|\bconst\b")


def _needs_auto(key: str, lang: str) -> bool:
    """Câu còn chữ tiếng Việt sau khi dịch theo từ điển (không tính tên thương hiệu) -> cần dịch tự động."""
    if len(key) > 4500 or _CODE.search(key):
        return False
    static = translate_text(key, lang)
    return bool(HAS_VI.search(_BRAND.sub("", static)))


def translate_html(html: str, lang: str = "en") -> str:
    auto = {}
    if auto_translate.enabled() and lang in ("en", "zh"):
        pending = set()
        for m in TEXT_NODE.finditer(html):
            key = " ".join(_html.unescape(m.group(1)).split())
            if HAS_VI.search(key) and _needs_auto(key, lang):
                pending.add(key)
        for m in ATTR.finditer(html):
            key = " ".join(_html.unescape(m.group(2)).split())
            if HAS_VI.search(key) and _needs_auto(key, lang):
                pending.add(key)
        if pending:
            auto = auto_translate.translate_batch(sorted(pending), lang)

    def tr(raw: str) -> str:
        new = translate_text(raw, lang)
        if auto and HAS_VI.search(_BRAND.sub("", new)):
            hit = auto.get(" ".join(_html.unescape(raw).split()))
            if hit:
                return _html.escape(hit, quote=False)
        return new

    def node(m):
        raw = m.group(1)
        new = tr(raw)
        if new is raw or new == raw:
            return m.group(0)
        lead = raw[:len(raw) - len(raw.lstrip())]
        trail = raw[len(raw.rstrip()):]
        return ">" + lead + new + trail + "<"

    def attr(m):
        new = tr(m.group(2))
        return m.group(0) if new == m.group(2) else f'{m.group(1)}="{_html.escape(new, quote=True) if auto else new}"'

    return ATTR.sub(attr, TEXT_NODE.sub(node, html))


_JSON_TEXT_KEYS = ("error", "message", "errors")


def translate_json(payload, lang: str = "en"):
    """Dịch các thông báo (khóa error/message/errors) trong phản hồi JSON của trang khách hàng."""
    if isinstance(payload, dict):
        return {k: (translate_json_value(v, lang) if k in _JSON_TEXT_KEYS else v) for k, v in payload.items()}
    return payload


def translate_json_value(v, lang: str):
    if isinstance(v, str):
        out = translate_text(v, lang)
        if auto_translate.enabled() and HAS_VI.search(_BRAND.sub("", out)):
            out = auto_translate.translate_batch([" ".join(v.split())], lang).get(" ".join(v.split()), out)
        return out
    if isinstance(v, list):
        return [translate_json_value(x, lang) for x in v]
    if isinstance(v, dict):
        return {k: translate_json_value(x, lang) for k, x in v.items()}
    return v