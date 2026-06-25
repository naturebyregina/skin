/* ===================================================================
   NATURE BY REGINA — interactions & refined animation
   =================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initHeaderScroll();
    initReveal();
    initFloatingLeaves();
    initParallax();
    initCardTilt();
    initMobileMenu();
    initAccordions();
    refreshCart();
    syncWishlist();
});

/* ---------- Sticky header shadow ---------- */
function initHeaderScroll() {
    const header = document.querySelector('.header');
    if (!header) return;
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}

/* ---------- Scroll reveal ---------- */
function initReveal() {
    const els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
            if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
    els.forEach((el) => io.observe(el));
}

/* ---------- Floating botanical leaves ---------- */
function initFloatingLeaves() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const leaves = ['🌿', '🍃', '🌱', '🌾'];
    const spawn = () => {
        const leaf = document.createElement('div');
        leaf.className = 'leaf-float';
        leaf.textContent = leaves[Math.floor(Math.random() * leaves.length)];
        leaf.style.left = Math.random() * 100 + 'vw';
        const dur = 6 + Math.random() * 5;
        leaf.style.fontSize = (1.4 + Math.random() * 1.8) + 'rem';
        leaf.style.animation = `leaf-fall ${dur}s linear forwards`;
        document.body.appendChild(leaf);
        setTimeout(() => leaf.remove(), dur * 1000);
    };
    setInterval(spawn, 1600);
    // a quick initial flurry
    [0, 400, 800, 1200].forEach((t) => setTimeout(spawn, t));
}

/* ---------- Parallax on hero orb / botanicals ---------- */
function initParallax() {
    const layers = document.querySelectorAll('[data-parallax]');
    if (!layers.length) return;
    window.addEventListener('scroll', () => {
        const y = window.scrollY;
        layers.forEach((l) => {
            const speed = parseFloat(l.dataset.parallax) || 0.2;
            l.style.transform = `translateY(${y * speed}px)`;
        });
    }, { passive: true });
}

/* ---------- Subtle per-card tilt on hover ---------- */
function initCardTilt() {
    if (window.matchMedia('(hover: none)').matches) return;
    document.querySelectorAll('.card, .blog-card').forEach((card) => {
        card.addEventListener('mousemove', (e) => {
            const r = card.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5;
            const y = (e.clientY - r.top) / r.height - 0.5;
            card.style.transform = `translateY(-10px) perspective(900px) rotateX(${-y * 5}deg) rotateY(${x * 5}deg)`;
        });
        card.addEventListener('mouseleave', () => { card.style.transform = ''; });
    });
}

/* ---------- Mobile menu ---------- */
function initMobileMenu() {
    const burger = document.querySelector('.hamburger');
    const menu = document.querySelector('.mobile-menu');
    if (!burger || !menu) return;
    burger.addEventListener('click', () => menu.classList.add('open'));
    menu.querySelector('.mobile-close')?.addEventListener('click', () => menu.classList.remove('open'));
    menu.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => menu.classList.remove('open')));
}

/* ---------- Accordions (product page) ---------- */
function initAccordions() {
    // open-by-default items
    document.querySelectorAll('.acc-item.open .acc-body').forEach((body) => {
        body.style.maxHeight = body.scrollHeight + 'px';
    });
    document.querySelectorAll('.acc-head').forEach((head) => {
        head.addEventListener('click', () => {
            const item = head.closest('.acc-item');
            const body = item.querySelector('.acc-body');
            const open = item.classList.toggle('open');
            body.style.maxHeight = open ? body.scrollHeight + 'px' : 0;
        });
    });
}

/* ---------- Cart ---------- */
function refreshCart() {
    fetch('/api/cart/get').then((r) => r.json()).then((d) => {
        document.querySelectorAll('.cart-badge').forEach((b) => {
            b.textContent = d.count;
            b.style.display = d.count > 0 ? 'inline-flex' : 'none';
        });
    }).catch(() => {});
}

function addCart(id, qty = 1) {
    fetch('/api/cart/add', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: id, quantity: qty })
    }).then((r) => r.json()).then((d) => {
        if (d.success) {
            toast('Added to your cart 🌿');
            document.querySelectorAll('.cart-badge').forEach((b) => {
                b.textContent = d.count; b.style.display = 'inline-flex';
                b.style.animation = 'none'; void b.offsetHeight; b.style.animation = 'pulse-scale 0.6s var(--ease)';
            });
        }
    });
}

/* ---------- Wishlist ---------- */
function syncWishlist() {
    fetch('/api/wishlist/ids').then((r) => r.json()).then((d) => {
        const ids = d.ids || [];
        document.querySelectorAll('.wish-btn').forEach((b) => {
            const on = ids.includes(parseInt(b.dataset.id));
            b.classList.toggle('active', on);
            b.textContent = on ? '♥' : '♡';
        });
    }).catch(() => {});
}

function toggleWish(ev, id) {
    ev.preventDefault(); ev.stopPropagation();
    const btn = ev.currentTarget;
    fetch('/api/wishlist/toggle', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: id })
    }).then((r) => {
        if (r.status === 401) { toast('Please sign in to save favourites'); setTimeout(() => location.href = '/login', 1200); return null; }
        return r.json();
    }).then((d) => {
        if (!d) return;
        btn.classList.toggle('active', d.added);
        btn.textContent = d.added ? '♥' : '♡';
        toast(d.added ? 'Saved to wishlist ♥' : 'Removed from wishlist');
    });
}

/* ---------- Toast ---------- */
function toast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => { t.style.animation = 'slide-in-right 0.4s var(--ease) reverse'; setTimeout(() => t.remove(), 400); }, 2400);
}

/* ---------- Chat ---------- */
function toggleChat() {
    const modal = document.getElementById('chat-modal');
    if (!modal) return;
    const showing = modal.style.display === 'block';
    modal.style.display = showing ? 'none' : 'block';
    if (!showing) document.getElementById('chat-text')?.focus();
}

function sendChat() {
    const inp = document.getElementById('chat-text');
    const msg = inp.value.trim();
    if (!msg) return;
    const box = document.getElementById('chat-messages');
    box.insertAdjacentHTML('beforeend', `<div class="msg user"><p>${escapeHtml(msg)}</p></div>`);
    inp.value = '';
    box.scrollTop = box.scrollHeight;

    const typing = document.createElement('div');
    typing.className = 'typing';
    typing.innerHTML = '<span></span><span></span><span></span>';
    box.appendChild(typing);
    box.scrollTop = box.scrollHeight;

    fetch('/api/chat/send', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    }).then((r) => r.json()).then((d) => {
        setTimeout(() => {
            typing.remove();
            box.insertAdjacentHTML('beforeend', `<div class="msg assistant"><p>${escapeHtml(d.response)}</p></div>`);
            box.scrollTop = box.scrollHeight;
        }, 700);
    });
}

function chatKey(e) { if (e.key === 'Enter') sendChat(); }

function escapeHtml(s) {
    const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
}

/* ---------- Newsletter ---------- */
function submitNewsletter(e) {
    e.preventDefault();
    const input = e.target.querySelector('input[type="email"]');
    fetch('/api/newsletter', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: input.value })
    }).then((r) => r.json()).then((d) => {
        if (d.success) { toast('Welcome to the family ✨'); input.value = ''; }
        else toast(d.error || 'Please try again');
    });
    return false;
}

/* ---------- Auth ---------- */
function handleLogin(e) {
    e.preventDefault();
    post('/login', { email: val('email'), password: val('password') }, (d) => {
        if (d.success) {
            toast('Welcome back 🌿');
            setTimeout(() => location.href = d.is_admin ? '/admin' : '/account', 900);
        } else err(d.error);
    });
}

function handleRegister(e) {
    e.preventDefault();
    post('/register', {
        first_name: val('first_name'), last_name: val('last_name'),
        email: val('email'), password: val('password')
    }, (d) => {
        if (d.success) { toast('Account created ✨'); setTimeout(() => location.href = '/account', 900); }
        else err(d.error);
    });
}

/* ---------- Reviews ---------- */
function submitReview(e, productId) {
    e.preventDefault();
    const rating = document.querySelector('input[name="rating"]:checked');
    const comment = document.getElementById('review-comment').value.trim();
    if (!rating || !comment) { toast('Please add a rating and a comment'); return; }
    fetch('/api/review/add', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, rating: rating.value, comment })
    }).then((r) => {
        if (r.status === 401) { toast('Please sign in to leave a review'); setTimeout(() => location.href = '/login', 1200); return null; }
        return r.json();
    }).then((d) => {
        if (d && d.success) { toast('Thank you for your review 💚'); setTimeout(() => location.reload(), 1000); }
    });
}

/* ---------- Quantity stepper ---------- */
function stepQty(delta) {
    const el = document.getElementById('qty-val');
    let v = parseInt(el.textContent) + delta;
    if (v < 1) v = 1;
    el.textContent = v;
}
function addCartWithQty(id) {
    const v = parseInt(document.getElementById('qty-val').textContent) || 1;
    addCart(id, v);
}

/* ---------- Helpers ---------- */
function val(id) { return document.getElementById(id).value; }
function err(m) { const e = document.getElementById('error'); if (e) e.textContent = m; }
function post(url, body, cb) {
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        .then((r) => r.json()).then(cb);
}
