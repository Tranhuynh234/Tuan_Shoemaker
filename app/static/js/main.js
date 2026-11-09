/* Giày Tuấn */
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-toggle-password]').forEach(function (toggle) {
        toggle.addEventListener('change', function () {
            var field = document.querySelector(toggle.getAttribute('data-toggle-password'));
            if (field) field.type = toggle.checked ? 'text' : 'password';
        });
    });

    var openBtn = document.getElementById('openMenuBtn');
    var closeBtn = document.getElementById('closeMenuBtn');
    var sideMenu = document.getElementById('sideMenu');
    var overlay = document.getElementById('menuOverlay');

    function closeMenu() {
        if (sideMenu) sideMenu.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    }

    if (sideMenu && overlay) {
        document.querySelectorAll('[data-open-menu], #openMenuBtn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                sideMenu.classList.add('active');
                overlay.classList.add('active');
                document.body.style.overflow = 'hidden'; 
            });
        });
        if (closeBtn) closeBtn.addEventListener('click', closeMenu);
        overlay.addEventListener('click', closeMenu);
        document.addEventListener('keydown', function (e) { 
            if (e.key === 'Escape') closeMenu(); 
        });
    }

    // Xác nhận trước thao tác quan trọng: <form data-confirm="...">
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!window.confirm(form.dataset.confirm)) {
                e.preventDefault();
                e.stopImmediatePropagation();
            }
        });
    });

    // Trạng thái loading
    document.querySelectorAll('form[method="post"]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (e.defaultPrevented) return;
            var btn = e.submitter || form.querySelector('button[type="submit"]');
            if (!btn || btn.dataset.noLoading !== undefined) return;
            setTimeout(function () {
                form.querySelectorAll('button[type="submit"]').forEach(function (b) { b.disabled = true; });
                btn.classList.add('is-loading');
                if (btn.dataset.loadingText) btn.textContent = btn.dataset.loadingText;
            }, 0);
        });
    });

    // Đóng thông báo
    document.querySelectorAll('.flash .flash-close').forEach(function (b) {
        b.addEventListener('click', function () { b.closest('.flash').remove(); });
    });

    // Thư viện ảnh sản phẩm
    var mainImg = document.getElementById('galleryMain');
    document.querySelectorAll('[data-gallery-thumb]').forEach(function (t) {
        t.addEventListener('click', function () {
            if (mainImg) mainImg.src = t.dataset.src;
            document.querySelectorAll('[data-gallery-thumb]').forEach(function (x) { x.classList.remove('active'); });
            t.classList.add('active');
        });
    });

    // Thẻ sản phẩm: hover đổi ảnh + rê chuột vào ảnh nhỏ để xem từng ảnh
    document.querySelectorAll('[data-card]').forEach(function (card) {
        var main = card.querySelector('.card-main');
        if (!main) return;
        var thumbs = card.querySelectorAll('.card-thumb');
        var preloaded = false;

        function show(src) {
            if (src && main.getAttribute('src') !== src) main.src = src;
            thumbs.forEach(function (t) { t.classList.toggle('active', t.dataset.src === src); });
        }
        function preload() { // tải trước để lúc đổi ảnh không bị nháy
            if (preloaded) return;
            preloaded = true;
            thumbs.forEach(function (t) { new Image().src = t.dataset.src; });
        }
        function enter() { preload(); show(main.dataset.hover); }
        function leave() { show(main.dataset.default); }

        card.addEventListener('mouseenter', enter);
        card.addEventListener('mouseleave', leave);
        card.addEventListener('focusin', function () { if (card.matches(':focus-visible')) enter(); });
        card.addEventListener('focusout', function (e) { if (!card.contains(e.relatedTarget)) leave(); });
        thumbs.forEach(function (t) {
            t.addEventListener('mouseenter', function () { show(t.dataset.src); });
        });
    });

    // Giao diện sáng/tối
    var themeBtn = document.getElementById('themeToggle');

    if (themeBtn) {
        themeBtn.addEventListener('click', function () {
            var currentTheme = document.documentElement.getAttribute('data-theme');
            var next = currentTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', next);
            try {
                localStorage.setItem('theme', next);
            } catch (e) { }
        });
    }

    // Xử lý popup chọn ngôn ngữ
    const langWrapper = document.querySelector(".language-wrapper");
    const langPopup = document.getElementById("languagePopup");
    const langToggle = document.getElementById("languageToggle");

    if (langWrapper && langPopup) {
        langWrapper.addEventListener("click", function (event) {
            event.stopPropagation();
            // Nếu click vào các thành phần bên trong popup chọn ngôn ngữ (như radio, nút lưu), để yên cho form hoạt động
            if (event.target.closest('.language-popup') && !event.target.closest('#languageToggle')) {
                return;
            }
            langPopup.hidden = !langPopup.hidden;
            if (langToggle) {
                langToggle.setAttribute('aria-expanded', langPopup.hidden ? 'false' : 'true');
            }
        });

        document.addEventListener("click", function (event) {
            if (!event.target.closest(".language-wrapper")) {
                langPopup.hidden = true;
                if (langToggle) langToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }
    // Bảng người dùng (Đăng ký / Đăng nhập / Sáng-tối / Ngôn ngữ)
    var userBtn = document.getElementById('userMenuToggle');
    var userPopup = document.getElementById('userPopup');

    if (userBtn && userPopup) {
        function setUserMenu(open) {
            userPopup.hidden = !open;
            userBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        userBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            setUserMenu(userPopup.hidden);
        });
        document.addEventListener('click', function (event) {
            if (!event.target.closest('.user-menu')) setUserMenu(false);
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') setUserMenu(false);
        });
    }
    // Hamburger menu (máy tính bảng / điện thoại)
    var navToggle = document.getElementById('navToggle');
    var navHeader = navToggle ? navToggle.closest('.header') : null;
    if (navToggle && navHeader) {
        function setNav(open) {
            navHeader.classList.toggle('nav-open', open);
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            navToggle.setAttribute('aria-label', open ? 'Đóng menu điều hướng' : 'Mở menu điều hướng');
        }
        navToggle.addEventListener('click', function (event) {
            event.stopPropagation();
            setNav(!navHeader.classList.contains('nav-open'));
        });
        document.addEventListener('click', function (event) {
            if (!event.target.closest('.header')) setNav(false);
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') setNav(false);
        });
        // Bấm "Sản phẩm" mở menu bên: đóng hamburger để không chồng lên nhau
        var navProducts = document.getElementById('openMenuBtn');
        if (navProducts) navProducts.addEventListener('click', function () { setNav(false); });
        window.addEventListener('resize', function () { if (window.innerWidth > 992) setNav(false); });
    }
    var heroHeader = document.querySelector('.header.header-hero');

    if (heroHeader) {
        function syncHeader() {
            heroHeader.classList.toggle('is-scrolled', window.scrollY > 40);
        }
        syncHeader();
        window.addEventListener('scroll', syncHeader, { passive: true });
    }
});

// Bấm Sản phẩm nam / nữ / Phụ kiện để xổ ra hoặc thu lại.

(function () {
    document.querySelectorAll('[data-sub-toggle]').forEach(function (a) {
        a.addEventListener('click', function (e) {
            e.preventDefault();
            var li = a.parentElement;
            var willOpen = !li.classList.contains('open');

            document.querySelectorAll('.side-menu-list li.has-sub.open').forEach(function (o) {
                o.classList.remove('open');
                o.querySelector('[data-sub-toggle]').setAttribute('aria-expanded', 'false');
            });

            if (willOpen) {
                li.classList.add('open');
                a.setAttribute('aria-expanded', 'true');
            }
        });
    });
})();

/* Trang Portfolio */
(() => {
    const stage = document.querySelector('.story-stage');
    const pin = document.querySelector('.story-pin');
    const paper = document.querySelector('.sp-paper');
    const track = document.getElementById('scrollTrack');
    const win = document.querySelector('.sp-window');
    const panels = [...document.querySelectorAll('.sp-panel')];
    const spreads = panels.map(p => p.querySelector('.bk'));
    const layers = [...document.querySelectorAll('.sp-bg')];
    const progress = document.getElementById('chapterProgressBar');
    const counter = document.getElementById('currentChapter');
    const titleEl = document.getElementById('currentTitle');
    const dots = [...document.querySelectorAll('.sp-dots a')];
    if (!stage || !pin || !paper || !track || !win || !panels.length) return;

    const mobile = window.matchMedia('(max-width: 900px)');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');

    let maxX = 0, activeIndex = -1, activeLayer = 0, ticking = false;

    /* ---------- Dò ảnh ---------- */
    const ROOT = stage.dataset.imgRoot || '/static/images/';
    const FOLDERS = ['port', 'portfolio'];
    const EXTS = ['jpg', 'png', 'jpeg', 'webp', 'JPG', 'PNG'];
    const found = new Map();
    function findImage(names) {
        const key = names.join('|');
        if (found.has(key)) return found.get(key);
        const urls = [];
        FOLDERS.forEach(f => names.forEach(n => EXTS.forEach(e => urls.push(`${ROOT}${f}/${n}.${e}`))));
        const p = new Promise(resolve => {
            let i = 0;
            (function next() {
                if (i >= urls.length) return resolve(null);
                const probe = new Image(), url = urls[i++];
                probe.onload = () => resolve(url);
                probe.onerror = next;
                probe.src = url;
            })();
        });
        found.set(key, p);
        return p;
    }
    // Ảnh trong các khung
    document.querySelectorAll('.bk-photo img[data-name]').forEach(img => {
        findImage([img.dataset.name]).then(url => {
            if (!url) return;
            img.src = url;
            img.parentNode.classList.add('ok');
        });
    });

    /* ---------- Dò video ---------- */
    function findVideo(names) {
        const urls = [];
        ['port', 'portfolio', 'video', 'videos', ''].forEach(f => names.forEach(n => ['mp4', 'MP4', 'webm'].forEach(e => urls.push(`${ROOT}${f ? f + '/' : ''}${n}.${e}`))));
        return new Promise(resolve => {
            let i = 0;
            (function next() {
                if (i >= urls.length) return resolve(null);
                const probe = document.createElement('video'), url = urls[i++];
                probe.preload = 'metadata'; probe.muted = true;
                probe.onloadedmetadata = () => resolve(url);
                probe.onerror = next;
                probe.src = url;
            })();
        });
    }

    /* ---------- Bìa Kinh Thành ---------- */
    const cover = document.getElementById('spCover');
    if (cover) {
        document.body.classList.add('sp-locked');
        window.scrollTo(0, 0);
        const enter = document.getElementById('spEnter');
        const video = document.getElementById('spVideo');
        const unroll = document.getElementById('spUnroll');
        const skip = document.getElementById('spSkip');
        let hasVideo = false, unrollOk = false, finished = false, guard = null;

        // file video bìa 
        if (video && cover.dataset.video) {
            findVideo(cover.dataset.video.split(',')).then(url => {
                if (!url) return;
                video.src = url;
                video.load();
                hasVideo = true;
                cover.classList.add('has-video');
            });
        }

        // video cuốn chiếu: kiểm tra đã tải được chưa
        if (unroll) {
            if (unroll.readyState >= 1) unrollOk = true;
            unroll.addEventListener('loadedmetadata', () => { unrollOk = true; });
            unroll.addEventListener('error', () => console.warn('Không tải được video cuốn chiếu:', unroll.currentSrc || unroll.src));
        }

        // Y như bản gốc của bạn (dùng cho BỎ QUA / lỗi)
        function finish() {
            if (finished) return;
            finished = true;
            clearTimeout(guard);
            if (video) video.pause();
            if (unroll) { unroll.pause(); unroll.classList.add('out'); }
            if (skip) skip.hidden = true;
            document.body.classList.add('sp-revealed');
            cover.classList.add('done');
            setTimeout(() => {
                cover.hidden = true;
                document.body.classList.remove('sp-locked');
            }, reduced.matches ? 0 : 1300);
        }

        // Chuyển cảnh: cuốn chiếu thật hiện dần, video mờ đi, rồi bìa mờ theo
        function crossfade() {
            if (finished) return;
            finished = true;
            clearTimeout(guard);
            if (skip) skip.hidden = true;
            document.body.classList.add('sp-revealed');
            unroll.classList.add('out');
            setTimeout(() => cover.classList.add('done'), 500);
            setTimeout(() => {
                cover.hidden = true;
                document.body.classList.remove('sp-locked');
            }, reduced.matches ? 0 : 1800);
        }

        // Video Kinh Thành hết -> video cuốn chiếu chạy
        function playUnroll() {
            if (finished) return;
            if (!unroll || !unrollOk || reduced.matches) return finish();
            clearTimeout(guard);
            unroll.addEventListener('ended', crossfade, { once: true });
            unroll.addEventListener('error', finish, { once: true });
            unroll.addEventListener('timeupdate', function onT() {
                if (unroll.duration && unroll.duration - unroll.currentTime < 0.8) {
                    unroll.removeEventListener('timeupdate', onT);
                    crossfade();
                }
            });
            guard = setTimeout(() => { if (unroll.currentTime < 0.1) finish(); }, 6000);
            unroll.currentTime = 0;
            unroll.classList.add('show');
            const p = unroll.play();
            if (p && p.catch) p.catch(finish);
        }

        enter.addEventListener('mouseenter', () => { if (!hasVideo && !cover.classList.contains('opening')) cover.classList.add('peek'); });
        enter.addEventListener('mouseleave', () => cover.classList.remove('peek'));
        enter.addEventListener('click', () => {
            if (cover.classList.contains('opening') || cover.classList.contains('playing')) return;
            cover.classList.remove('peek');

             if (hasVideo) {
                document.body.classList.add('sp-match');   
                cover.classList.add('playing');
                // Bấm xong mới phát video
                cover.classList.add('playing');
                if (skip) skip.hidden = false;
                video.addEventListener('ended', playUnroll, { once: true });   
                video.addEventListener('error', finish, { once: true });
                const p = video.play();
                if (p && p.catch) p.catch(() => { video.muted = true; video.play().catch(finish); });
                guard = setTimeout(() => { if (video.currentTime < 0.1) finish(); }, 8000);
                return;
            }

            // Không có video: giữ hiệu ứng hai cánh cửa mở như cũ
            cover.classList.add('opening');
            document.body.classList.add('sp-revealed');
            setTimeout(() => {
                cover.hidden = true;
                document.body.classList.remove('sp-locked');
            }, reduced.matches ? 0 : 1900);
        });
        if (skip) skip.addEventListener('click', finish);
    }

    /* ---------- Ảnh chiếu chỉ ---------- */
    if (paper.dataset.names) {
        findImage(paper.dataset.names.split(',')).then(url => {
            if (!url) return;
            const im = new Image();
            im.onload = () => {
                const W = im.naturalWidth, H = im.naturalHeight;
                let bx = 0, by = 0, bw = W, bh = H;
                try {
                    const sc = Math.min(1, 700 / W), cw = Math.max(1, Math.round(W * sc)), ch = Math.max(1, Math.round(H * sc));
                    const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
                    const cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(im, 0, 0, cw, ch);
                    const d = cx.getImageData(0, 0, cw, ch).data;
                    let x0 = cw, y0 = ch, x1 = -1, y1 = -1;
                    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) {
                        if (d[(y * cw + x) * 4 + 3] > 60) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
                    }
                    if (x1 > x0 && y1 > y0) { bx = x0 / sc; by = y0 / sc; bw = (x1 - x0 + 1) / sc; bh = (y1 - y0 + 1) / sc; }
                } catch (e) { /* không đọc được điểm ảnh: dùng cả ảnh */ }
                paper.style.setProperty('--sp-ratio', (bw / bh).toFixed(4));
                paper.style.setProperty('--sp-img-size', `${(W / bw * 100).toFixed(3)}% ${(H / bh * 100).toFixed(3)}%`);
                paper.style.setProperty('--sp-img-pos', `${W > bw ? (bx / (W - bw) * 100).toFixed(3) : 0}% ${H > bh ? (by / (H - bh) * 100).toFixed(3) : 0}%`);
                paper.style.setProperty('--sp-scroll-img', `url("${url}")`);
                paper.classList.add('has-img');
                setup();
            };
            im.src = url;
        });
    }
    if (cover && cover.dataset.names) {
        findImage(cover.dataset.names.split(',')).then(url => {
            if (url) cover.style.setProperty('--sp-cover', `url("${url}")`);
        });
    }

    /* ---------- Nền video theo mục ----------
       Mỗi mục lấy video theo data-bg (vd: bg-about -> images/port/bg-about.mp4 hoặc .webm).
       Chưa có video / video lỗi thì giữ ảnh nền cũ. Video tắt tiếng, tự lặp, chỉ phát video của mục đang xem. */
    const bgStage = document.getElementById('storyBackground');
    const bgShade = bgStage && bgStage.querySelector('.sp-bg-shade');
    const bgVids = new Map();
    function playBg(i) {
        const r = bgVids.get(i);
        if (!r || !r.el || reduced.matches) return;
        const pr = r.el.play();
        if (pr && pr.catch) pr.catch(() => {});
    }
    function bgVideo(i) {
        if (bgVids.has(i)) return bgVids.get(i);
        const rec = { el: null };
        bgVids.set(i, rec);
        const panel = panels[i];
        if (!bgStage || !panel || !panel.dataset.bg || reduced.matches) return rec;
        findVideo([panel.dataset.bg]).then(url => {
            if (!url) return;
            const v = document.createElement('video');
            v.className = 'sp-bgv';
            v.muted = true; v.loop = true; v.playsInline = true;
            v.setAttribute('muted', ''); v.setAttribute('playsinline', ''); v.setAttribute('aria-hidden', 'true');
            v.preload = 'auto';
            v.addEventListener('loadeddata', () => {
                v.classList.add('ready');
                if (activeIndex === i) playBg(i);
            });
            v.src = url;
            if (activeIndex === i) v.classList.add('on');
            bgStage.insertBefore(v, bgShade);
            rec.el = v;
        });
        return rec;
    }
    function syncBgVideos(index) {
        bgVideo(index);
        bgVideo(index + 1);                       // tải trước mục kế tiếp cho khỏi giật
        bgVids.forEach((r, i) => {
            if (!r.el) return;
            r.el.classList.toggle('on', i === index);
            if (i === index) playBg(i);
            else setTimeout(() => { if (activeIndex !== i) r.el.pause(); }, 900);
        });
    }
    document.addEventListener('visibilitychange', () => { if (!document.hidden) playBg(activeIndex); });
    document.addEventListener('click', () => playBg(activeIndex), { once: true });   // một số trình duyệt chỉ cho phát sau lần chạm đầu

    /* ---------- Đổi nền theo mục ---------- */
    function setBackground(index) {
        if (index === activeIndex) return;
        activeIndex = index;
        const panel = panels[index];
        const next = layers[1 - activeLayer];
        next.style.backgroundImage = 'none';
        if (panel.dataset.bg) {
            findImage([panel.dataset.bg]).then(url => {
                if (url && activeIndex === index) next.style.backgroundImage = `url("${url}")`;
            });
        }
        next.classList.add('on');
        layers[activeLayer].classList.remove('on');
        activeLayer = 1 - activeLayer;

        syncBgVideos(index);

        counter.textContent = `${String(index + 1).padStart(2, '0')} / ${String(panels.length).padStart(2, '0')}`;
        titleEl.textContent = panel.dataset.title || '';
        dots.forEach((dot, i) => {
            if (i === index) dot.setAttribute('aria-current', 'location'); else dot.removeAttribute('aria-current');
        });
    }

    function setup() {
        if (mobile.matches) {
            stage.style.height = 'auto';
            track.style.transform = 'none';
            spreads.forEach(s => { if (s) { s.style.transform = ''; s.style.opacity = ''; } });
            stage.style.removeProperty('--sp-panel-w');
            maxX = 0;
            return;
        }
        stage.style.setProperty('--sp-panel-w', `${win.clientWidth}px`);
        maxX = Math.max(0, track.scrollWidth - win.clientWidth);
        stage.style.height = `${maxX + pin.offsetHeight}px`;
        update();
    }

    function update() {
        ticking = false;
        if (mobile.matches) return;
        const travelled = Math.min(maxX, Math.max(0, -stage.getBoundingClientRect().top));
        track.style.transform = `translate3d(${-travelled}px, 0, 0)`;
        const ratio = maxX > 0 ? travelled / maxX : 0;
        progress.style.width = `${ratio * 100}%`;
        setBackground(Math.min(panels.length - 1, Math.round(ratio * (panels.length - 1))));
    }

    function requestUpdate() {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(update);
    }

    dots.forEach((dot, index) => {
        dot.addEventListener('click', event => {
            event.preventDefault();
            if (mobile.matches) { panels[index].scrollIntoView({ behavior: reduced.matches ? 'auto' : 'smooth' }); return; }
            const stageTop = window.scrollY + stage.getBoundingClientRect().top;
            const targetX = maxX * index / Math.max(1, panels.length - 1);
            window.scrollTo({ top: stageTop + targetX, behavior: reduced.matches ? 'auto' : 'smooth' });
        });
    });

    // Điện thoại
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(entries => {
            if (!mobile.matches) return;
            entries.forEach(e => { if (e.isIntersecting) setBackground(panels.indexOf(e.target)); });
        }, { rootMargin: '-45% 0px -45% 0px' });
        panels.forEach(p => io.observe(p));
    }

    /* ---------- Xem ảnh lớn ---------- */
    const box = document.getElementById('spLightbox');
    if (box) {
        const big = document.getElementById('spBig');
        const cap = document.getElementById('spCap');
        document.querySelectorAll('.sp-open').forEach(btn => {
            btn.addEventListener('click', () => {
                big.src = btn.dataset.src;
                big.alt = btn.dataset.cap;
                cap.textContent = btn.dataset.cap;
                if (box.showModal) box.showModal(); else box.setAttribute('open', '');
            });
        });
        const close = () => { if (box.close) box.close(); else box.removeAttribute('open'); };
        document.getElementById('spClose').addEventListener('click', close);
        box.addEventListener('click', e => { if (e.target === box) close(); });
    }

    /* ---------- Tự căn giữa ---------- */
    let snapTimer = null;
    function snapToPanel() {
        if (mobile.matches || maxX <= 0 || panels.length < 2) return;
        const stageTop = window.scrollY + stage.getBoundingClientRect().top;
        const travelled = window.scrollY - stageTop;
        if (travelled < 0 || travelled > maxX) return;           
        const step = maxX / (panels.length - 1);
        const target = stageTop + Math.round(travelled / step) * step;
        if (Math.abs(target - window.scrollY) > 2) {
            window.scrollTo({ top: target, behavior: reduced.matches ? 'auto' : 'smooth' });
        }
    }
    window.addEventListener('scroll', () => {
        clearTimeout(snapTimer);
        snapTimer = setTimeout(snapToPanel, 160);
    }, { passive: true });

    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', setup);
    window.addEventListener('load', setup);
    mobile.addEventListener && mobile.addEventListener('change', setup);

    setBackground(0);
    setup();
})();

/* Trang chủ */

// Video banner + video dịch vụ
(function () {
    function tryPlay(v) {
        var p = v.play();
        if (p && p.catch) p.catch(function () { /* bị chặn: giữ poster/khung hình đầu */ });
    }
    document.querySelectorAll('#heroVideo, [data-service-video]').forEach(function (v) {
        v.muted = true;
        tryPlay(v);
        v.addEventListener('loadeddata', function () { if (v.paused && !v.dataset.userPaused) tryPlay(v); });
    });
    document.querySelectorAll('[data-service-toggle]').forEach(function (btn) {
        var v = btn.parentElement.querySelector('video');
        if (!v) return;
        btn.addEventListener('click', function () {
            var pausing = !v.paused;
            if (pausing) { v.pause(); v.dataset.userPaused = '1'; } else { delete v.dataset.userPaused; tryPlay(v); }
            btn.setAttribute('aria-pressed', pausing ? 'true' : 'false');
            btn.setAttribute('aria-label', (pausing ? btn.dataset.labelPlay : btn.dataset.labelPause) || (pausing ? 'Phát video' : 'Tạm dừng video'));
            btn.firstElementChild.textContent = pausing ? '▶' : 'II';
        });
    });
})();

// Banner hình ảnh thương hiệu: 2 slider (trái/phải) dùng chung 1 bộ đếm 2s nên luôn đổi ảnh cùng lúc
(function () {
    var INTERVAL = 2000;
    var sliders = Array.prototype.map.call(document.querySelectorAll('[data-bm-slider]'), function (box) {
        return { slides: box.querySelectorAll('.bm-slide'), current: 0 };
    }).filter(function (s) { return s.slides.length > 1; });
    if (!sliders.length) return;
    var timer = null;

    function preload(s, i) {
        var el = s.slides[i % s.slides.length], src = el && el.getAttribute('src');
        if (src) new Image().src = src;
    }
    function next() {
        sliders.forEach(function (s) {
            var target = (s.current + 1) % s.slides.length;
            s.slides[s.current].classList.remove('is-active');
            s.slides[target].classList.add('is-active');
            s.current = target;
            preload(s, target + 1);
        });
    }
    function start() { if (!timer) timer = setInterval(next, INTERVAL); }
    function stop() { clearInterval(timer); timer = null; }

    sliders.forEach(function (s) { preload(s, 1); });
    start();
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });
})();

// Slideshow thương hiệu + Cổ điển / Hiện đại / Thể thao
(function () {
    var INTERVAL = 2000;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    document.querySelectorAll('[data-slideshow]').forEach(function (box, boxIndex) {
        var slides = box.querySelectorAll('.slide');
        var dots = box.querySelectorAll('.dot');
        if (slides.length < 2) return;
        var current = 0, timer = null;

        function show(i) {
            current = (i + slides.length) % slides.length;
            slides.forEach(function (s, k) { s.classList.toggle('active', k === current); });
            dots.forEach(function (d, k) { d.classList.toggle('active', k === current); });
        }
        function start() {
            if (reduceMotion || timer) return;
            timer = setInterval(function () { show(current + 1); }, INTERVAL);
        }
        function stop() { clearInterval(timer); timer = null; }

        dots.forEach(function (d) {
            d.addEventListener('click', function () {
                show(parseInt(d.dataset.index, 10));
                stop(); start();
            });
        });
        box.addEventListener('mouseenter', stop);
        box.addEventListener('mouseleave', start);
        document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });

        setTimeout(start, boxIndex * 500);
    });
})();

document.addEventListener('DOMContentLoaded', () => {
    const footer = document.querySelector('.footer');
    const btns = document.querySelectorAll('.chat-btn');
    if (!footer || !btns.length) return;

    let ticking = false;
    const update = () => {
        const top = footer.getBoundingClientRect().top;
        btns.forEach(b => {
            const r = b.getBoundingClientRect();
            b.classList.toggle('on-footer', r.top + r.height / 2 >= top);
        });
        ticking = false;
    };
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
});

/* Form sản phẩm admin: nhập kích cỡ, tồn kho và ảnh ngay trên trang, lưu một lần. */
(function () {
    var form = document.getElementById('productForm');
    if (!form) return;
    var cfg = JSON.parse(document.getElementById('pfConfig').textContent);
    var dirty = false, submitting = false;
    function $(id) { return document.getElementById(id); }
    function markDirty() { dirty = true; }
    form.addEventListener('input', markDirty);
    form.addEventListener('change', markDirty);
    window.addEventListener('beforeunload', function (e) {
        if (dirty && !submitting) { e.preventDefault(); e.returnValue = ''; }
    });
    var cancel = $('pfCancel');
    if (cancel) cancel.addEventListener('click', function (e) {
        if (dirty && !window.confirm('Các thay đổi chưa lưu sẽ mất. Bạn vẫn muốn rời trang?')) e.preventDefault();
        else submitting = true;
    });

    /* ---------- Giá ---------- */
    var price = $('pfPrice'), sale = $('pfSale'), hint = $('pfPriceHint');
    function vnd(n) { return Number(n).toLocaleString('vi-VN') + ' ₫'; }
    function priceHint() {
        var p = parseInt(price.value, 10), s = parseInt(sale.value, 10);
        sale.setCustomValidity('');
        hint.classList.remove('pf-err');
        if (isNaN(p)) { hint.textContent = ''; return; }
        if (!isNaN(s) && s > p) {
            sale.setCustomValidity('Giá khuyến mãi không được lớn hơn giá gốc');
            hint.classList.add('pf-err');
            hint.textContent = 'Giá khuyến mãi không được lớn hơn giá gốc.';
        } else if (!isNaN(s) && s < p) {
            hint.textContent = 'Khách thấy: ' + vnd(s) + ' (giảm ' + Math.floor((p - s) * 100 / p) + '% so với ' + vnd(p) + ')';
        } else {
            hint.textContent = 'Khách thấy: ' + vnd(p);
        }
    }
    price.addEventListener('input', priceHint);
    sale.addEventListener('input', priceHint);
    priceHint();

    /* ---------- Kích cỡ / tồn kho ---------- */
    var tbody = $('pfVariants'), tpl = $('pfRowTpl'), emptyMsg = $('pfVariantsEmpty');
    function rows() { return Array.prototype.slice.call(tbody.querySelectorAll('tr')); }
    function cell(row, name) { return row.querySelector('[name="' + name + '"]'); }
    function refreshVariants() {
        emptyMsg.hidden = rows().length > 0;
    }
    function addRow(size, color, stock, focus) {
        var row = tpl.content.firstElementChild.cloneNode(true);
        cell(row, 'variant_size').value = size || '';
        cell(row, 'variant_color').value = color || '';
        cell(row, 'variant_stock').value = stock === undefined ? '' : stock;
        tbody.appendChild(row);
        refreshVariants();
        if (focus) cell(row, 'variant_size').focus();
        return row;
    }
    function hasVariant(size, color) {
        return rows().some(function (r) {
            return cell(r, 'variant_size').value.trim().toUpperCase() === size.toUpperCase() &&
                   cell(r, 'variant_color').value.trim().toLowerCase() === color.toLowerCase();
        });
    }
    function blankRows() {
        rows().forEach(function (r) {
            var empty = !cell(r, 'variant_id').value && !cell(r, 'variant_size').value.trim() &&
                        !cell(r, 'variant_color').value.trim() && !cell(r, 'variant_stock').value.trim();
            if (empty) r.remove();
        });
    }
    $('pfAddRow').addEventListener('click', function () { markDirty(); addRow('', '', undefined, true); });
    tbody.addEventListener('click', function (e) {
        var b = e.target.closest('.pf-del');
        if (!b) return;
        b.closest('tr').remove();
        markDirty();
        refreshVariants();
    });
    tbody.addEventListener('input', function (e) {
        e.target.classList.remove('pf-bad');
        if (e.target.name === 'variant_stock') refreshVariants();
    });
    tbody.addEventListener('keydown', function (e) {
        if (e.key !== 'Enter') return;
        e.preventDefault();  // Enter trong bảng không được gửi form
        var row = e.target.closest('tr'), name = e.target.name;
        var next = row.nextElementSibling;
        if (next) cell(next, name).focus();
        else if (name === 'variant_stock') { markDirty(); addRow('', '', undefined, true); }
        else e.target.closest('td').nextElementSibling.querySelector('input').focus();
    });
    function quickAdd() {
        var raw = $('pfQuickSizes').value.trim();
        if (!raw) { $('pfQuickSizes').focus(); return; }
        var color = $('pfQuickColor').value.trim();
        var stock = $('pfQuickStock').value.trim();
        var sizes = [];
        raw.split(/[\s,;]+/).forEach(function (t) {
            var m = t.match(/^(\d+)\s*[-–]\s*(\d+)$/);
            if (m) {
                var a = parseInt(m[1], 10), b = parseInt(m[2], 10);
                if (a > b) { var x = a; a = b; b = x; }
                for (var i = a; i <= b && i - a < 60; i++) sizes.push(String(i));
            } else if (t) sizes.push(t);
        });
        blankRows();
        sizes.forEach(function (s) { if (!hasVariant(s, color)) addRow(s, color, stock); });
        $('pfQuickSizes').value = '';
        markDirty();
        refreshVariants();
        var first = rows()[0];
        if (first) cell(first, 'variant_stock').focus();
    }
    $('pfQuickAdd').addEventListener('click', quickAdd);
    ['pfQuickSizes', 'pfQuickColor', 'pfQuickStock'].forEach(function (id) {
        $(id).addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); quickAdd(); } });
    });
    if (!rows().length && !form.querySelector('[name="name"]').value) addRow('', '', undefined, false);
    refreshVariants();

    /* ---------- Hình ảnh ---------- */
    var fileInput = $('pfFile'), tiles = $('pfTiles'), keepBox = $('pfKeep'), primaryInput = $('pfPrimary');
    var imgMsg = $('pfImgMsg'), drop = $('pfDrop');
    var items = [], primary = null;
    var okTypes = ['image/jpeg', 'image/png', 'image/webp'];
    var maxBytes = cfg.maxMb * 1024 * 1024;

    cfg.images.forEach(function (im) {
        var it = {type: 'old', id: im.id, url: im.url};
        items.push(it);
        if (im.primary) primary = it;
    });

    function showImgMsg(list) {
        imgMsg.hidden = !list.length;
        imgMsg.innerHTML = '';
        list.forEach(function (t) { var d = document.createElement('div'); d.textContent = t; imgMsg.appendChild(d); });
    }
    function sync() {
        if (!primary || items.indexOf(primary) < 0) primary = items[0] || null;
        var dt = new DataTransfer(), newIdx = 0, primaryVal = '';
        keepBox.innerHTML = '';
        items.forEach(function (it) {
            var val;
            if (it.type === 'old') {
                var h = document.createElement('input');
                h.type = 'hidden'; h.name = 'keep_image'; h.value = it.id;
                keepBox.appendChild(h);
                val = 'old:' + it.id;
            } else {
                dt.items.add(it.file);
                val = 'new:' + newIdx++;
            }
            if (it === primary) primaryVal = val;
        });
        fileInput.files = dt.files;
        primaryInput.value = primaryVal;
    }
    function render() {
        tiles.innerHTML = '';
        items.forEach(function (it) {
            var d = document.createElement('div');
            d.className = 'pf-tile' + (it === primary ? ' is-primary' : '');
            var img = document.createElement('img');
            img.src = it.url; img.alt = '';
            var x = document.createElement('button');
            x.type = 'button'; x.className = 'pf-x'; x.textContent = '×'; x.title = 'Xóa ảnh';
            x.addEventListener('click', function () {
                if (it.type === 'new') URL.revokeObjectURL(it.url);
                items.splice(items.indexOf(it), 1);
                markDirty(); sync(); render(); showImgMsg([]);
            });
            var star = document.createElement('button');
            star.type = 'button'; star.className = 'pf-star';
            star.textContent = it === primary ? '★ Ảnh chính' : 'Đặt làm ảnh chính';
            star.addEventListener('click', function () { primary = it; markDirty(); sync(); render(); });
            d.appendChild(img); d.appendChild(x); d.appendChild(star);
            if (it.type === 'new') {
                var tag = document.createElement('span');
                tag.className = 'pf-new'; tag.textContent = 'Mới';
                d.appendChild(tag);
            }
            tiles.appendChild(d);
        });
    }
    function addFiles(list) {
        var errors = [];
        Array.prototype.forEach.call(list, function (f) {
            if (okTypes.indexOf(f.type) < 0) { errors.push('“' + f.name + '”: chỉ nhận ảnh JPG, PNG hoặc WEBP.'); return; }
            if (f.size > maxBytes) { errors.push('“' + f.name + '”: lớn hơn ' + cfg.maxMb + 'MB.'); return; }
            if (items.length >= cfg.maxImages) { errors.push('Tối đa ' + cfg.maxImages + ' ảnh, đã bỏ qua “' + f.name + '”.'); return; }
            var dup = items.some(function (it) {
                return it.type === 'new' && it.file.name === f.name && it.file.size === f.size && it.file.lastModified === f.lastModified;
            });
            if (dup) return;
            var it = {type: 'new', file: f, url: URL.createObjectURL(f)};
            items.push(it);
            if (!primary) primary = it;
        });
        showImgMsg(errors);
        markDirty(); sync(); render();
    }
    fileInput.addEventListener('change', function () {
        // Mỗi lần chọn là thêm ảnh vào danh sách; sync() ghi lại input.files gồm tất cả ảnh mới
        addFiles(Array.prototype.slice.call(fileInput.files));
    });
    ['dragenter', 'dragover'].forEach(function (ev) {
        drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('is-over'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
        drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('is-over'); });
    });
    drop.addEventListener('drop', function (e) { if (e.dataTransfer && e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
    sync(); render();

    var errBox = $('pfErrors');
    form.addEventListener('submit', function (e) {
        var problems = [], seen = {};
        rows().forEach(function (r) { r.querySelectorAll('input').forEach(function (i) { i.classList.remove('pf-bad'); }); });
        rows().forEach(function (r) {
            var sz = cell(r, 'variant_size'), co = cell(r, 'variant_color'), st = cell(r, 'variant_stock');
            var any = sz.value.trim() || co.value.trim() || st.value.trim() || cell(r, 'variant_id').value;
            if (!any) return;
            if (!sz.value.trim()) { sz.classList.add('pf-bad'); problems.push('Có dòng chưa nhập size.'); return; }
            if (st.value.trim() && !/^\d+$/.test(st.value.trim())) { st.classList.add('pf-bad'); problems.push('Tồn kho size ' + sz.value.trim() + ' phải là số nguyên không âm.'); }
            var key = sz.value.trim().toUpperCase() + '|' + co.value.trim().toLowerCase();
            if (seen[key]) { sz.classList.add('pf-bad'); problems.push('Size ' + sz.value.trim() + (co.value.trim() ? ' / ' + co.value.trim() : '') + ' bị nhập trùng.'); }
            seen[key] = true;
        });
        if (problems.length) {
            e.preventDefault();
            errBox.hidden = false;
            errBox.innerHTML = '';
            problems.forEach(function (t) { var d = document.createElement('div'); d.textContent = t; errBox.appendChild(d); });
            errBox.scrollIntoView({behavior: 'smooth', block: 'center'});
            return;
        }
        errBox.hidden = true;
        sync();
        submitting = true;
    }, true);
})();

(function () {
    var root = document.querySelector('.ab');
    var items = document.querySelectorAll('.ax-reveal');
    if (!root || !items.length || !('IntersectionObserver' in window) ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var vh = window.innerHeight;
    items.forEach(function (el) {
        if (el.getBoundingClientRect().top < vh * 0.95) el.classList.add('is-in');
    });

    root.classList.add('ax-js');
    var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
            if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
        });
    }, { rootMargin: '0px 0px 10% 0px', threshold: 0 });   // hiện trước khi chạm đáy màn hình
    items.forEach(function (el) { if (!el.classList.contains('is-in')) io.observe(el); });
})();

/* Trang Giới thiệu, mục 06: ảnh banner thu nhỏ về giữa, các ảnh khác bung ra theo cuộn.
   Dán vào CUỐI file JS chính (ngoài DOMContentLoaded cũng được, script nằm cuối trang). */
(function () {
    var sec = document.querySelector('.xp');
    if (!sec) return;
    var track = sec.querySelector('.xp-track');
    var pin = sec.querySelector('.xp-pin');
    var stage = sec.querySelector('.xp-stage');
    var hero = sec.querySelector('.xp-c');
    var copy = hero && hero.querySelector('.xp-copy');
    var shade = hero && hero.querySelector('.xp-shade');
    if (!track || !pin || !stage || !hero) return;

    var others = Array.prototype.slice.call(stage.querySelectorAll('.xp-ph')).filter(function (el) { return el !== hero; });
    var mq = window.matchMedia('(min-width: 993px) and (prefers-reduced-motion: no-preference)');
    var INSET = 10;      // lề của banner lúc đầu (px)
    var START = 0.05;    // phần cuộn đầu giữ nguyên banner
    var SPAN = 0.68;     // đoạn cuộn dành cho hiệu ứng; phần còn lại giữ bố cục cuối
    var W = 0, H = 0, hdr = 110, fin = null, finHero = null, live = false, ticking = false;

    function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
    function lerp(a, b, t) { return a + (b - a) * t; }
    function easeOut(x) { return 1 - Math.pow(1 - x, 3); }
    function easeInOut(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }

    function box(el) { return { l: el.offsetLeft, t: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight }; }

    function measure() {
        // bỏ style nội suy để đọc đúng vị trí cuối do CSS quy định
        hero.style.left = hero.style.top = hero.style.width = hero.style.height = '';
        others.forEach(function (el) { el.style.transform = ''; el.style.opacity = ''; });
        W = stage.clientWidth;
        H = stage.clientHeight;
        hdr = parseFloat(getComputedStyle(pin).top) || 0;
        finHero = box(hero);
        fin = others.map(box);
    }

    function render() {
        ticking = false;
        if (!live) return;
        var range = track.offsetHeight - pin.offsetHeight;
        var raw = range > 0 ? clamp((hdr - track.getBoundingClientRect().top) / range, 0, 1) : 1;
        var t = clamp((raw - START) / SPAN, 0, 1);
        var m = easeInOut(t);

        hero.style.left = lerp(INSET, finHero.l, m) + 'px';
        hero.style.top = lerp(0, finHero.t, m) + 'px';
        hero.style.width = lerp(W - INSET * 2, finHero.w, m) + 'px';
        hero.style.height = lerp(H, finHero.h, m) + 'px';
        if (copy) {
            var a = 1 - clamp(t / 0.3, 0, 1);
            copy.style.opacity = a;
            copy.style.transform = 'translateY(' + (-14 * (1 - a)) + 'px)';
        }
        if (shade) shade.style.opacity = 1 - clamp(t / 0.55, 0, 1);

        others.forEach(function (el, i) {
            var d = parseFloat(el.dataset.d) || 0;
            var e = easeOut(clamp((t - d) / (1 - d), 0, 1));
            var f = fin[i];
            var dx = (W / 2 - (f.l + f.w / 2)) * (1 - e);
            var dy = (H / 2 - (f.t + f.h / 2)) * (1 - e);
            var s = 0.06 + 0.94 * e;
            el.style.transform = 'translate3d(' + dx + 'px,' + dy + 'px,0) scale(' + s + ')';
            el.style.opacity = clamp(e * 4, 0, 1);
        });
    }

    function request() { if (!ticking) { ticking = true; requestAnimationFrame(render); } }

    function enable() {
        if (live) return;
        sec.classList.add('is-anim');
        live = true;
        measure();
        render();
    }
    function disable() {
        if (!live) return;
        live = false;
        sec.classList.remove('is-anim');
        hero.removeAttribute('style');
        if (copy) copy.removeAttribute('style');
        if (shade) shade.removeAttribute('style');
        others.forEach(function (el) { el.removeAttribute('style'); });
    }
    function sync() { if (mq.matches) enable(); else disable(); }

    window.addEventListener('scroll', request, { passive: true });
    window.addEventListener('resize', function () { if (live) { measure(); request(); } });
    window.addEventListener('load', function () { if (live) { measure(); request(); } });
    if (mq.addEventListener) mq.addEventListener('change', sync); else if (mq.addListener) mq.addListener(sync);
    sync();
})();


/* Đăng nhập / Đăng ký: bảng giữa trượt qua lại, đổi địa chỉ trang mà không tải lại.
   Dán vào CUỐI file JS chính. Chưa có JS thì nút vẫn là link /register và /login bình thường. */
(function () {
    function init() {
        var stage = document.getElementById('authStage');
        if (!stage) return;

        var swBox = stage.querySelector('.auth-switch');
        var panels = { login: stage.querySelector('.auth-panel--login'), register: stage.querySelector('.auth-panel--register') };
        var copies = stage.querySelectorAll('.auth-copy');
        var urls = { login: stage.dataset.loginUrl, register: stage.dataset.registerUrl };
        var titles = { login: stage.dataset.titleLogin, register: stage.dataset.titleRegister };
        var registerPath = new URL(urls.register, window.location.href).pathname.replace(/\/+$/, '');
        var search = window.location.search;                 // giữ ?next=... khi chuyển qua lại
        var mobile = window.matchMedia('(max-width: 820px)');
        var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
        var timer = null;

        function lock(el, on) {                              // phần đang ẩn: bỏ khỏi bàn phím + trình đọc màn hình
            if (!el) return;
            el.toggleAttribute('inert', on);
            if (on) el.setAttribute('aria-hidden', 'true'); else el.removeAttribute('aria-hidden');
        }

        function render(mode) {
            stage.dataset.mode = mode;
            Object.keys(panels).forEach(function (k) { lock(panels[k], k !== mode); });
            copies.forEach(function (c) { lock(c, c.dataset.showIn !== mode); });
            if (titles[mode]) document.title = titles[mode];
        }

        function stretch() {                                 // hiệu ứng bảng giãn ra giữa chừng
            if (!swBox || mobile.matches || reduced.matches) return;
            swBox.classList.remove('is-moving');
            void swBox.offsetWidth;
            swBox.classList.add('is-moving');
            clearTimeout(timer);
            timer = setTimeout(function () { swBox.classList.remove('is-moving'); }, 1300);
        }

        function go(mode, push) {
            if (stage.dataset.mode === mode) return;
            document.querySelectorAll('.flash').forEach(function (f) { f.remove(); });   // bỏ thông báo lỗi của form cũ
            stretch();
            render(mode);
            if (push) { try { history.pushState({ authMode: mode }, '', urls[mode] + search); } catch (err) { /* mở file trực tiếp: bỏ qua */ } }
            if (!mobile.matches) {
                var first = panels[mode].querySelector('input:not([type=hidden])');
                setTimeout(function () { if (first) first.focus({ preventScroll: true }); }, reduced.matches ? 0 : 700);
            }
        }

        stage.addEventListener('click', function (e) {
            var a = e.target.closest('[data-auth-go]');
            if (!a || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            go(a.dataset.authGo, true);
        });

        window.addEventListener('popstate', function () {   // nút Back / Forward của trình duyệt
            var path = window.location.pathname.replace(/\/+$/, '');
            go(path === registerPath ? 'register' : 'login', false);
        });

        try { history.replaceState({ authMode: stage.dataset.mode }, ''); } catch (err) { }
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

// Bảng dữ liệu trên điện thoại: gắn nhãn cột (data-label) từ <th> để CSS hiển thị dạng thẻ.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('table:not(.pf-table)').forEach(function (table) {
        var heads = Array.prototype.map.call(table.querySelectorAll('thead th'), function (th) {
            return th.textContent.replace(/\s+/g, ' ').trim();
        });
        if (!heads.length) return;
        table.querySelectorAll('tbody tr').forEach(function (tr) {
            var col = 0;
            Array.prototype.forEach.call(tr.children, function (cell) {
                if (cell.tagName === 'TD' && heads[col]) cell.setAttribute('data-label', heads[col]);
                col += cell.colSpan || 1;
            });
        });
    });
});