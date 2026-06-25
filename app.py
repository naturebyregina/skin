#!/usr/bin/env python3
"""Nature by Regina — luxury natural skincare e-commerce platform (Flask)."""
import os, sqlite3, random, json, urllib.request, urllib.error, urllib.parse
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, jsonify, session,
                   redirect, url_for, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'nature-by-regina-secret-2026'
DATABASE = 'database.db'

# --- Admin & payments configuration (override with environment variables) --- #
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@naturebyregina.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')  # change in production!
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')   # pk_test_xxx
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')   # sk_test_xxx

# Email (SMTP) — e.g. Gmail: smtp.gmail.com / 587 / app password
SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USER or 'hello@naturebyregina.com')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL', SMTP_USER)  # admin alerts

# Telegram bot — create with @BotFather, get chat id from @userinfobot
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Editable site settings (Developer Mode). Grouped for the admin form.
SETTINGS_SCHEMA = [
    ('Brand', [
        ('brand_name', 'Brand Name', 'Nature by Regina'),
        ('tagline', 'Tagline', '…Treat yourself, stay healthy.'),
        ('promo_text', 'Top Promo Bar', '✦ Free shipping on orders over ₦80,000 · Handcrafted in small batches ✦'),
    ]),
    ('Images', [
        ('logo_image', 'Logo', '/static/img/logo.jpg'),
        ('hero_image', 'Homepage Hero Image', '/static/img/hero.jpg'),
        ('story_image', 'Story / About Image', '/static/img/story.jpg'),
    ]),
    ('Homepage Video', [
        ('hero_video', 'Homepage Video (optional — plays in the "In Motion" section)', ''),
    ]),
    ('Homepage Hero', [
        ('hero_eyebrow', 'Hero Eyebrow', 'Pure · Natural · Handcrafted'),
        ('hero_title', 'Hero Title', 'Radiant skin, rooted in nature.'),
        ('hero_subtitle', 'Hero Subtitle', 'Luxury natural skincare handcrafted in small batches with shea butter, plantain ash and botanical oils. Treat yourself, stay healthy.'),
    ]),
    ('Payment (Bank)', [
        ('bank_accounts', 'Bank Accounts (one per line: Bank | Account Name | Number)',
         'Access Bank | Nature by Regina | 0123456789'),
        ('free_ship_threshold', 'Free Shipping Over (₦)', '80000'),
    ]),
    ('Payment Keys (Paystack)', [
        ('paystack_public', 'Paystack Public Key', ''),
        ('paystack_secret', 'Paystack Secret Key', ''),
    ]),
    ('Email (SMTP)', [
        ('smtp_host', 'SMTP Host', ''),
        ('smtp_port', 'SMTP Port', '587'),
        ('smtp_user', 'SMTP Username', ''),
        ('smtp_pass', 'SMTP Password', ''),
        ('smtp_from', 'From Email', ''),
        ('notify_email', 'Admin Notify Email', ''),
    ]),
    ('Telegram Alerts', [
        ('telegram_token', 'Bot Token', ''),
        ('telegram_chat', 'Chat ID', ''),
    ]),
    ('Ad Studio (Image → Video)', [
        ('video_provider', 'Provider: replicate / huggingface / google (Veo)', 'replicate'),
        ('video_api_key', 'Video API Key', ''),
        ('video_model', 'Model slug/version (optional)', ''),
    ]),
    ('Contact', [
        ('contact_phone', 'Phone', '+234 800 000 0000'),
        ('contact_email', 'Email', 'hello@naturebyregina.com'),
        ('contact_address', 'Address', 'Lagos, Nigeria · Nationwide delivery'),
        ('contact_hours', 'Opening Hours', 'Mon–Sat, 9am – 6pm'),
    ]),
    ('Social Links', [
        ('social_instagram', 'Instagram URL', '#'),
        ('social_whatsapp', 'WhatsApp URL', '#'),
        ('social_facebook', 'Facebook URL', '#'),
        ('social_tiktok', 'TikTok URL', '#'),
    ]),
    ('Theme (Developer)', [
        ('color_primary', 'Primary Green', '#2d5a3d'),
        ('color_accent', 'Accent Gold', '#c9a763'),
    ]),
]
DEFAULT_SETTINGS = {k: v for _, fields in SETTINGS_SCHEMA for k, _, v in fields}

# Loyalty tiers: name -> (min points, perk)
LOYALTY_TIERS = [
    ('Bronze', 0, '5% birthday reward'),
    ('Silver', 500, 'Free local shipping'),
    ('Gold', 1500, 'Early access + 10% off'),
    ('Platinum', 3000, 'VIP gifts + 15% off'),
]


# --------------------------------------------------------------------------- #
#  Database
# --------------------------------------------------------------------------- #
def init_db():
    db = sqlite3.connect(DATABASE)
    c = db.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL, phone TEXT, address TEXT,
        city TEXT, state TEXT, loyalty_points INTEGER DEFAULT 0,
        loyalty_tier TEXT DEFAULT 'Bronze', referral_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
        description TEXT, ingredients TEXT, benefits TEXT, price REAL NOT NULL,
        image TEXT, category TEXT NOT NULL, stock INTEGER DEFAULT 10,
        rating REAL DEFAULT 5.0, reviews_count INTEGER DEFAULT 0, badge TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, order_code TEXT UNIQUE NOT NULL, user_id INTEGER,
        subtotal REAL NOT NULL, tax REAL NOT NULL, shipping REAL NOT NULL, total REAL NOT NULL,
        status TEXT DEFAULT 'pending', shipping_method TEXT, payment_method TEXT,
        address TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
        name TEXT, quantity INTEGER NOT NULL, price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id), FOREIGN KEY(product_id) REFERENCES products(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT NOT NULL, is_assistant BOOLEAN DEFAULT 0,
        image_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL, user_id INTEGER, author TEXT,
        rating REAL NOT NULL, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id), FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, product_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS newsletter (
        id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS blog_posts (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
        excerpt TEXT, body TEXT, image TEXT, category TEXT, author TEXT,
        read_time TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY, type TEXT, path TEXT NOT NULL, name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS testimonials (
        id INTEGER PRIMARY KEY, author TEXT NOT NULL, role TEXT, rating REAL DEFAULT 5.0,
        comment TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    db.commit()
    db.close()
    migrate()


def migrate():
    """Add any columns introduced after an earlier version of the DB was created."""
    db = sqlite3.connect(DATABASE)
    c = db.cursor()
    wanted = {
        'products': {'ingredients': 'TEXT', 'benefits': 'TEXT', 'badge': 'TEXT'},
        'orders': {'address': 'TEXT', 'receipt_path': 'TEXT'},
        'order_items': {'name': 'TEXT'},
        'reviews': {'author': 'TEXT'},
        'users': {'referral_code': 'TEXT', 'is_admin': 'INTEGER DEFAULT 0', 'photo': 'TEXT'},
    }
    for table, cols in wanted.items():
        try:
            existing = {row[1] for row in c.execute(f'PRAGMA table_info({table})').fetchall()}
        except sqlite3.OperationalError:
            continue
        for col, ctype in cols.items():
            if col not in existing:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {ctype}')
    # If products predate the richer seed data, refresh ingredients/benefits/badge.
    row = c.execute("SELECT ingredients FROM products WHERE slug='black-soap'").fetchone()
    if row and not row[0]:
        c.execute("DELETE FROM products")
        c.execute("DELETE FROM reviews")
    db.commit()
    db.close()


def seed():
    db = sqlite3.connect(DATABASE)
    c = db.cursor()

    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        products = [
            ('African Black Soap', 'black-soap',
             'Authentic African black soap, handcrafted from plantain ash, cocoa pods and shea butter. A centuries-old cleansing ritual that gently purifies, balances and renews all skin types.',
             'Plantain skin ash, cocoa pod ash, raw shea butter, palm kernel oil, coconut oil',
             'Deep cleansing|Evens tone|Soothes blemishes|Gentle for daily use',
             3500, '🧼', 'soaps', 50, 5.0, 3, 'Bestseller'),
            ('Liquid Black Soap', 'liquid-black-soap',
             'A concentrated liquid form of our beloved black soap. Lathers richly for face, body and hair — the convenience of a wash with the soul of tradition.',
             'African black soap base, aloe vera, glycerin, vitamin E, essential oils',
             'Multi-use|Rich lather|Hydrating|Travel friendly',
             4500, '🧴', 'soaps', 40, 4.9, 2, None),
            ('Body Butter', 'body-butter',
             'A whipped cloud of raw shea and cocoa butter infused with cold-pressed oils. Melts into skin to seal in moisture and leave a soft, luminous finish.',
             'Raw shea butter, cocoa butter, sweet almond oil, jojoba oil, vitamin E',
             'Deeply moisturizing|Non-greasy|Softens skin|All-day comfort',
             5500, '🧈', 'moisturizers', 35, 5.0, 4, 'Loved'),
            ('Lemon Soap', 'lemon-soap',
             'Cold-process lemon soap brightened with real citrus extract. An energizing daily cleanse that refreshes dull skin and awakens the senses.',
             'Saponified coconut & olive oil, lemon extract, lemon essential oil, shea butter',
             'Brightening|Energizing|Clarifying|Fresh scent',
             3000, '🍋', 'soaps', 60, 4.8, 1, None),
            ('Turmeric Scrub', 'turmeric-scrub',
             'A golden exfoliating scrub blending turmeric with fine natural grains. Sloughs away dullness to reveal smoother, more radiant skin.',
             'Turmeric, sugar crystals, coconut oil, honey, oat powder',
             'Exfoliating|Glow-boosting|Smooths texture|Brightens',
             4000, '✨', 'scrubs', 45, 4.9, 2, None),
            ('Face Serum', 'face-serum',
             'A lightweight botanical serum that absorbs in seconds. A daily dose of antioxidants and natural extracts for a dewy, radiant complexion.',
             'Hyaluronic acid, vitamin C, green tea extract, rosehip oil, niacinamide',
             'Hydrating|Radiance|Fast-absorbing|Antioxidant rich',
             6500, '💧', 'serums', 30, 5.0, 2, 'New'),
            ('Clay Mask', 'clay-mask',
             'A purifying clay mask that draws out impurities and refines pores. Detoxifies without stripping, leaving skin clear and balanced.',
             'Kaolin clay, bentonite clay, activated charcoal, aloe vera, tea tree oil',
             'Detoxifying|Pore-refining|Balancing|Clarifying',
             5000, '🎨', 'masks', 28, 4.9, 1, None),
            ('Anti-Stretch Oil', 'anti-stretch-oil',
             'A nourishing blend of natural oils crafted to improve skin elasticity and reduce the appearance of stretch marks over time.',
             'Bitter almond oil, rosehip oil, vitamin E, lavender oil, cocoa butter',
             'Improves elasticity|Reduces marks|Deeply nourishing|Gentle',
             7500, '🌿', 'oils', 25, 5.0, 1, None),
        ]
        c.executemany('''INSERT INTO products
            (name,slug,description,ingredients,benefits,price,image,category,stock,rating,reviews_count,badge)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', products)

    c.execute('SELECT COUNT(*) FROM reviews')
    if c.fetchone()[0] == 0:
        sample_reviews = [
            (1, 'Amara O.', 5.0, 'My skin has never felt cleaner. This is the only soap I use now — worth every naira.'),
            (1, 'Tunde A.', 5.0, 'Cleared my back acne in two weeks. Genuinely impressed.'),
            (1, 'Ngozi E.', 4.5, 'Lovely and natural. The scent takes a little getting used to but the results are real.'),
            (3, 'Blessing K.', 5.0, 'This body butter is heaven. So rich and my skin glows all day.'),
            (3, 'Chidi M.', 5.0, 'A little goes a long way. Not greasy at all.'),
            (3, 'Fatima S.', 5.0, 'Bought it for my mum, now the whole family is hooked.'),
            (3, 'Ada U.', 4.5, 'Beautiful product, beautifully made.'),
            (5, 'Joy I.', 5.0, 'My face feels so smooth after. The glow is unreal.'),
            (5, 'Kemi B.', 4.5, 'Gentle enough for twice a week. Love it.'),
            (6, 'Ifeoma N.', 5.0, 'This serum is my new holy grail. Dewy skin in seconds.'),
            (6, 'Daniel O.', 5.0, 'Absorbs fast, no sticky feeling. Highly recommend.'),
            (2, 'Grace A.', 5.0, 'So convenient and the lather is amazing.'),
            (2, 'Samuel T.', 4.5, 'Use it for everything — face, body, even my hair.'),
            (4, 'Peace L.', 5.0, 'Fresh, zingy, and brightens my skin. A daily joy.'),
            (7, 'Halima Y.', 5.0, 'My pores have visibly shrunk. Magic clay!'),
            (8, 'Rita C.', 5.0, 'Helped fade my stretch marks after pregnancy. Thank you Regina!'),
        ]
        c.executemany('INSERT INTO reviews (product_id,author,rating,comment) VALUES (?,?,?,?)', sample_reviews)

    c.execute('SELECT COUNT(*) FROM blog_posts')
    if c.fetchone()[0] == 0:
        posts = [
            ('The Ancient Art of African Black Soap', 'art-of-african-black-soap',
             'Discover the centuries-old tradition behind our most-loved cleanser and why it belongs in your routine.',
             '''African black soap is more than a product — it is heritage. For generations across West Africa, families have crafted this soap by sun-drying plantain skins, cocoa pods and palm leaves, then roasting the ash and blending it with shea butter and natural oils.\n\nThe result is a gentle, mineral-rich cleanser that works for nearly every skin type. Unlike commercial soaps stripped of their character, black soap retains the vitamins A and E naturally found in its ingredients, along with antioxidants that help calm and balance the skin.\n\nHow to use it: wet the bar, work a small amount into a soft lather between your palms, and massage gently onto damp skin. A little goes a long way. Follow with our Body Butter to seal in moisture, and you have a complete ritual rooted in tradition.''',
             '🧼', 'Ingredients', "Regina's Team", '4 min read'),
            ('5 Signs Your Skin Is Craving Natural Care', 'signs-skin-craving-natural-care',
             'Tightness, dullness, breakouts — your skin speaks a language. Here is how to listen.',
             '''Your skin is your largest organ, and it has a way of telling you when something is off. Here are five signs it may be time to return to gentler, natural care.\n\n1. Tightness after cleansing. If your skin feels tight or squeaky, your cleanser is likely stripping its natural oils. Switch to a balancing option like our African Black Soap.\n\n2. Persistent dullness. A lack of glow often signals a build-up of dead skin. A weekly Turmeric Scrub can reveal the radiance underneath.\n\n3. Reactive redness. Harsh synthetics can leave skin inflamed. Natural, fragrance-light formulas help calm the barrier.\n\n4. Midday oiliness. Over-stripped skin overproduces oil to compensate. Hydration is the answer, not more cleansing.\n\n5. Rough texture. Gentle exfoliation followed by a rich Body Butter restores softness over time.''',
             '🌿', 'Skincare 101', "Regina's Team", '5 min read'),
            ('Building Your Glow-Up Routine on a Budget', 'glow-up-routine-on-a-budget',
             'A radiant complexion does not require ten steps. Here is a simple, affordable ritual that works.',
             '''Great skin is about consistency, not complication. You can build a complete routine with just a few thoughtfully chosen products.\n\nMorning: Cleanse with Lemon Soap to wake up the skin, then apply a few drops of Face Serum for hydration and radiance.\n\nEvening: Cleanse with African Black Soap to remove the day, then massage in Body Butter to nourish overnight.\n\nWeekly: Once or twice a week, exfoliate with Turmeric Scrub and treat yourself to a Clay Mask.\n\nThat is it. Five products, two minutes a day, and a glow that builds week after week. Treat yourself, stay healthy.''',
             '✨', 'Routines', "Regina's Team", '4 min read'),
        ]
        c.executemany('''INSERT INTO blog_posts (title,slug,excerpt,body,image,category,author,read_time)
            VALUES (?,?,?,?,?,?,?,?)''', posts)

    # Seed (or upgrade) the admin account
    admin = c.execute('SELECT id FROM users WHERE email = ?', (ADMIN_EMAIL,)).fetchone()
    if not admin:
        c.execute('''INSERT INTO users (email,password,first_name,last_name,is_admin,referral_code)
                     VALUES (?,?,?,?,1,?)''',
                  (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), 'Regina', 'Admin', 'REGINAADMIN'))
    else:
        c.execute('UPDATE users SET is_admin = 1 WHERE email = ?', (ADMIN_EMAIL,))

    # Attach real product photos (idempotent — also upgrades older emoji rows)
    photos = {
        'black-soap': '/static/img/black-soap.jpg',
        'liquid-black-soap': '/static/img/liquid-black-soap.jpg',
        'body-butter': '/static/img/body-butter.jpg',
        'lemon-soap': '/static/img/lemon-soap.jpg',
        'turmeric-scrub': '/static/img/turmeric-scrub.jpg',
        'face-serum': '/static/img/face-serum.jpg',
        'clay-mask': '/static/img/clay-mask.jpg',
        'anti-stretch-oil': '/static/img/anti-stretch-oil.jpg',
    }
    for slug, path in photos.items():
        c.execute('UPDATE products SET image = ? WHERE slug = ?', (path, slug))

    # Seed any missing default settings (keeps existing edited values)
    for key, val in DEFAULT_SETTINGS.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))

    # Seed a few testimonials
    if c.execute('SELECT COUNT(*) FROM testimonials').fetchone()[0] == 0:
        c.executemany('INSERT INTO testimonials (author,role,rating,comment) VALUES (?,?,?,?)', [
            ('Amara O.', 'Verified Customer', 5.0, 'My skin has never felt cleaner. The African Black Soap is the only soap I use now — worth every naira.'),
            ('Blessing K.', 'Verified Customer', 5.0, 'This body butter is heaven. So rich and my skin glows all day. The whole family is hooked.'),
            ('Ifeoma N.', 'Verified Customer', 5.0, 'The Face Serum is my new holy grail — dewy, radiant skin in seconds. Regina’s Team guided me perfectly.'),
        ])

    db.commit()
    db.close()


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def get_settings():
    """Return all site settings as a dict (falling back to defaults)."""
    s = dict(DEFAULT_SETTINGS)
    try:
        db = get_db()
        for row in db.execute('SELECT key, value FROM settings').fetchall():
            s[row['key']] = row['value']
        db.close()
    except sqlite3.OperationalError:
        pass
    return s


def conf(key, env_name=None, default=''):
    """Read a config value: admin Settings first, then environment, then default."""
    val = get_settings().get(key)
    if val:
        return val
    if env_name:
        return os.environ.get(env_name, default)
    return default


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return u


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u['is_admin']:
            return redirect('/login?admin=1')
        return f(*args, **kwargs)
    return wrapper


def tier_for_points(points):
    tier = LOYALTY_TIERS[0]
    for t in LOYALTY_TIERS:
        if points >= t[1]:
            tier = t
    return tier


# --------------------------------------------------------------------------- #
#  Public pages
# --------------------------------------------------------------------------- #
@app.route('/')
def index():
    db = get_db()
    featured = db.execute('SELECT * FROM products ORDER BY rating DESC, reviews_count DESC LIMIT 6').fetchall()
    testimonials = db.execute('SELECT * FROM testimonials ORDER BY created_at DESC LIMIT 6').fetchall()
    db.close()
    return render_template('index.html', featured_products=featured, testimonials=testimonials)


@app.route('/shop')
def shop():
    category = request.args.get('category', 'all')
    sort = request.args.get('sort', 'featured')
    db = get_db()
    if category != 'all':
        products = db.execute('SELECT * FROM products WHERE category = ?', (category,)).fetchall()
    else:
        products = db.execute('SELECT * FROM products').fetchall()
    cats = db.execute('SELECT DISTINCT category FROM products').fetchall()
    db.close()
    products = list(products)
    if sort == 'price-low':
        products.sort(key=lambda p: p['price'])
    elif sort == 'price-high':
        products.sort(key=lambda p: -p['price'])
    elif sort == 'rating':
        products.sort(key=lambda p: -p['rating'])
    return render_template('shop.html', products=products, categories=[c['category'] for c in cats],
                           active_category=category, active_sort=sort)


@app.route('/product/<slug>')
def product(slug):
    db = get_db()
    p = db.execute('SELECT * FROM products WHERE slug = ?', (slug,)).fetchone()
    if not p:
        db.close()
        abort(404)
    reviews = db.execute('SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC', (p['id'],)).fetchall()
    related = db.execute('SELECT * FROM products WHERE category = ? AND id != ? LIMIT 4', (p['category'], p['id'])).fetchall()
    if not related:
        related = db.execute('SELECT * FROM products WHERE id != ? ORDER BY RANDOM() LIMIT 4', (p['id'],)).fetchall()
    db.close()
    return render_template('product.html', product=p, reviews=reviews, related=related)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return jsonify({'success': True})
    return render_template('contact.html')


@app.route('/faq')
def faq():
    return render_template('faq.html')


@app.route('/blog')
def blog():
    db = get_db()
    posts = db.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('blog.html', posts=posts)


@app.route('/blog/<slug>')
def blog_post(slug):
    db = get_db()
    post = db.execute('SELECT * FROM blog_posts WHERE slug = ?', (slug,)).fetchone()
    if not post:
        db.close()
        abort(404)
    others = db.execute('SELECT * FROM blog_posts WHERE slug != ? ORDER BY RANDOM() LIMIT 2', (slug,)).fetchall()
    db.close()
    return render_template('blog_post.html', post=post, others=others)


# --------------------------------------------------------------------------- #
#  Auth
# --------------------------------------------------------------------------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        db = get_db()
        try:
            code = 'REGINA' + str(random.randint(1000, 9999))
            cur = db.execute('INSERT INTO users (email,password,first_name,last_name,referral_code) VALUES (?,?,?,?,?)',
                             (data['email'], generate_password_hash(data['password']),
                              data['first_name'], data['last_name'], code))
            db.commit()
            session['user_id'] = cur.lastrowid
            session['user_name'] = data['first_name']
            db.close()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            db.close()
            return jsonify({'success': False, 'error': 'An account with this email already exists'}), 400
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        db = get_db()
        u = db.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
        db.close()
        if u and check_password_hash(u['password'], data['password']):
            session['user_id'] = u['id']
            session['user_name'] = u['first_name']
            return jsonify({'success': True, 'is_admin': bool(u['is_admin'])})
        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# --------------------------------------------------------------------------- #
#  Account dashboard
# --------------------------------------------------------------------------- #
@app.route('/account')
@login_required
def account():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    orders = db.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    wishlist = db.execute('''SELECT p.* FROM wishlist w JOIN products p ON w.product_id=p.id
                             WHERE w.user_id = ?''', (session['user_id'],)).fetchall()
    db.close()
    tier = tier_for_points(user['loyalty_points'])
    # next tier
    next_tier = None
    for t in LOYALTY_TIERS:
        if t[1] > user['loyalty_points']:
            next_tier = t
            break
    return render_template('account.html', user=user, orders=orders, wishlist=wishlist,
                           tier=tier, next_tier=next_tier, tiers=LOYALTY_TIERS)


@app.route('/order/<code>')
@login_required
def order_track(code):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE order_code = ? AND user_id = ?',
                       (code, session['user_id'])).fetchone()
    if not order:
        db.close()
        abort(404)
    items = db.execute('SELECT * FROM order_items WHERE order_id = ?', (order['id'],)).fetchall()
    db.close()
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    return render_template('order_track.html', order=order, items=items, statuses=statuses)


@app.route('/wishlist')
@login_required
def wishlist_page():
    db = get_db()
    items = db.execute('''SELECT p.* FROM wishlist w JOIN products p ON w.product_id=p.id
                          WHERE w.user_id = ? ORDER BY w.created_at DESC''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('wishlist.html', products=items)


# --------------------------------------------------------------------------- #
#  Cart & checkout
# --------------------------------------------------------------------------- #
@app.route('/cart')
def cart():
    return render_template('cart.html')


@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data = request.get_json()
    if 'cart' not in session:
        session['cart'] = []
    db = get_db()
    p = db.execute('SELECT * FROM products WHERE id = ?', (data['product_id'],)).fetchone()
    db.close()
    if not p:
        return jsonify({'success': False}), 404
    qty = int(data.get('quantity', 1))
    for item in session['cart']:
        if item['id'] == p['id']:
            item['quantity'] += qty
            session.modified = True
            return jsonify({'success': True, 'count': sum(i['quantity'] for i in session['cart'])})
    session['cart'].append({'id': p['id'], 'name': p['name'], 'price': p['price'],
                            'image': p['image'], 'slug': p['slug'], 'quantity': qty})
    session.modified = True
    return jsonify({'success': True, 'count': sum(i['quantity'] for i in session['cart'])})


@app.route('/api/cart/update', methods=['POST'])
def cart_update():
    data = request.get_json()
    pid = data['product_id']
    qty = int(data['quantity'])
    cart = session.get('cart', [])
    cart = [i for i in cart if not (i['id'] == pid and qty <= 0)]
    for item in cart:
        if item['id'] == pid:
            item['quantity'] = qty
    session['cart'] = cart
    session.modified = True
    return cart_get()


@app.route('/api/cart/get')
def cart_get():
    cart = session.get('cart', [])
    sub = sum(i['price'] * i['quantity'] for i in cart)
    tax = round(sub * 0.075, 2)
    ship = 0 if sub > 80000 else 2500
    return jsonify({'items': cart, 'count': sum(i['quantity'] for i in cart),
                    'subtotal': sub, 'tax': tax, 'shipping': ship, 'total': round(sub+tax+ship, 2)})


@app.route('/checkout')
@login_required
def checkout():
    if not session.get('cart'):
        return redirect('/shop')
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return render_template('checkout.html', user=user)


@app.route('/api/order/create', methods=['POST'])
@login_required
def order_create():
    data = request.get_json()
    cart = session.get('cart', [])
    if not cart:
        return jsonify({'success': False, 'error': 'Cart is empty'}), 400
    sub = sum(i['price'] * i['quantity'] for i in cart)
    tax = round(sub * 0.075, 2)
    ship = float(data.get('shipping_cost', 2500))
    total = round(sub + tax + ship, 2)
    code = f"NBR-{datetime.now().year}-{random.randint(10000,99999)}"
    address = ', '.join(filter(None, [data.get('address'), data.get('city'), data.get('state')]))
    pay = data.get('payment_method')
    receipt = data.get('receipt_path')
    # Bank transfers await receipt verification; card/POD are confirmed immediately.
    status = 'pending' if pay == 'Bank Transfer' else 'confirmed'
    db = get_db()
    cur = db.execute('''INSERT INTO orders
        (order_code,user_id,subtotal,tax,shipping,total,shipping_method,payment_method,address,status,receipt_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (code, session['user_id'], sub, tax, ship, total,
         data.get('shipping_method'), pay, address, status, receipt))
    oid = cur.lastrowid
    for item in cart:
        db.execute('INSERT INTO order_items (order_id,product_id,name,quantity,price) VALUES (?,?,?,?,?)',
                   (oid, item['id'], item['name'], item['quantity'], item['price']))
    points = int(total // 100)
    db.execute('UPDATE users SET loyalty_points = loyalty_points + ? WHERE id = ?', (points, session['user_id']))
    user = db.execute('SELECT loyalty_points FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.execute('UPDATE users SET loyalty_tier = ? WHERE id = ?',
               (tier_for_points(user['loyalty_points'])[0], session['user_id']))
    cust = db.execute('SELECT email, first_name FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.commit()
    db.close()
    session['cart'] = []
    session.modified = True

    # Notifications (all graceful no-ops if not configured)
    items_txt = '\n'.join(f"  • {i['name']} ×{i['quantity']} — ₦{int(i['price']*i['quantity']):,}" for i in cart)
    try:
        send_email(cust['email'],
                   f"Your Nature by Regina order {code}",
                   f"Hi {cust['first_name']},\n\nThank you for your order! 🌿\n\n"
                   f"Order: {code}\nItems:\n{items_txt}\n\nTotal: ₦{int(total):,}\n"
                   f"Payment: {pay}\nShipping: {data.get('shipping_method')}\nDeliver to: {address}\n\n"
                   f"You earned {points} loyalty points. Track your order any time in your account.\n\n"
                   f"With love,\nRegina's Team")
        send_email(notify_email_addr(), f"🛒 New order {code} — ₦{int(total):,}",
                   f"New order {code}\nCustomer: {cust['first_name']} ({cust['email']})\n"
                   f"Total: ₦{int(total):,}\nPayment: {pay} ({status})\nItems:\n{items_txt}\nAddress: {address}")
        telegram_notify(
            f"🛒 <b>New order {code}</b>\nCustomer: {cust['first_name']}\n"
            f"Total: <b>₦{int(total):,}</b>\nPayment: {pay} ({status})\n{items_txt}")
    except Exception as e:
        print('[notify] error:', e)

    return jsonify({'success': True, 'order_code': code, 'total': total, 'points': points})


@app.route('/api/receipt/upload', methods=['POST'])
@login_required
def receipt_upload():
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    f = request.files['file']
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf'):
        return jsonify({'success': False, 'error': 'Upload an image or PDF of your receipt'}), 400
    folder = os.path.join('static', 'receipts')
    os.makedirs(folder, exist_ok=True)
    name = f"receipt-{session['user_id']}-{random.randint(10000,99999)}{ext}"
    f.save(os.path.join(folder, name))
    return jsonify({'success': True, 'path': f'/static/receipts/{name}'})


# --------------------------------------------------------------------------- #
#  Wishlist API
# --------------------------------------------------------------------------- #
@app.route('/api/wishlist/toggle', methods=['POST'])
def wishlist_toggle():
    if 'user_id' not in session:
        return jsonify({'success': False, 'login_required': True}), 401
    pid = request.get_json()['product_id']
    db = get_db()
    existing = db.execute('SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?',
                          (session['user_id'], pid)).fetchone()
    if existing:
        db.execute('DELETE FROM wishlist WHERE id = ?', (existing['id'],))
        added = False
    else:
        db.execute('INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)', (session['user_id'], pid))
        added = True
    db.commit()
    db.close()
    return jsonify({'success': True, 'added': added})


@app.route('/api/wishlist/ids')
def wishlist_ids():
    if 'user_id' not in session:
        return jsonify({'ids': []})
    db = get_db()
    rows = db.execute('SELECT product_id FROM wishlist WHERE user_id = ?', (session['user_id'],)).fetchall()
    db.close()
    return jsonify({'ids': [r['product_id'] for r in rows]})


# --------------------------------------------------------------------------- #
#  Reviews
# --------------------------------------------------------------------------- #
@app.route('/api/review/add', methods=['POST'])
def review_add():
    if 'user_id' not in session:
        return jsonify({'success': False, 'login_required': True}), 401
    data = request.get_json()
    db = get_db()
    db.execute('INSERT INTO reviews (product_id,user_id,author,rating,comment) VALUES (?,?,?,?,?)',
               (data['product_id'], session['user_id'], session.get('user_name', 'Customer'),
                float(data['rating']), data['comment']))
    rows = db.execute('SELECT AVG(rating) a, COUNT(*) n FROM reviews WHERE product_id = ?',
                      (data['product_id'],)).fetchone()
    db.execute('UPDATE products SET rating = ?, reviews_count = ? WHERE id = ?',
               (round(rows['a'], 1), rows['n'], data['product_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})


# --------------------------------------------------------------------------- #
#  Newsletter
# --------------------------------------------------------------------------- #
@app.route('/api/newsletter', methods=['POST'])
def newsletter():
    email = request.get_json().get('email', '').strip()
    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'Please enter a valid email'}), 400
    db = get_db()
    try:
        db.execute('INSERT INTO newsletter (email) VALUES (?)', (email,))
        db.commit()
        send_email(email, "Welcome to Nature by Regina 🌿",
                   "Thank you for joining the Nature by Regina family!\n\n"
                   "You'll be first to hear about new launches, skincare rituals and members-only offers — "
                   "plus 10% off your first order.\n\nTreat yourself, stay healthy.\nRegina's Team")
    except sqlite3.IntegrityError:
        pass
    db.close()
    return jsonify({'success': True})


# --------------------------------------------------------------------------- #
#  AI assistant — "Regina's Team"
# --------------------------------------------------------------------------- #
def assistant_reply(msg):
    m = msg.lower()
    db = get_db()
    products = db.execute('SELECT name, slug, price FROM products').fetchall()
    db.close()
    if any(w in m for w in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
        return "Hello, lovely! 🌿 Welcome to Nature by Regina. I'm here to help you find the perfect natural skincare. What are you looking for today?"
    if any(w in m for w in ['acne', 'pimple', 'breakout', 'spot']):
        return "For breakouts, our African Black Soap is a wonderful gentle cleanser, and the Clay Mask helps draw out impurities once or twice a week. Pair them for clearer, balanced skin. Would you like me to add either to your cart?"
    if any(w in m for w in ['dry', 'dryness', 'flaky', 'moistur']):
        return "Dry skin loves richness 💛 Our Body Butter is whipped shea and cocoa butter that melts in and seals moisture. The Face Serum is great for daily hydration too. Shall I show you?"
    if any(w in m for w in ['glow', 'dull', 'bright', 'radian', 'even tone']):
        return "For a glow-up ✨ try the Turmeric Scrub once or twice a week, followed by our Face Serum daily. Together they brighten and smooth beautifully."
    if any(w in m for w in ['stretch mark', 'pregnan']):
        return "Our Anti-Stretch Oil is crafted with rosehip and almond oils to improve elasticity over time. Many of our mums adore it. Would you like to learn more?"
    if 'black soap' in m:
        return "Our African Black Soap is 100% natural — handcrafted from plantain ash and shea butter. It cleanses gently and suits all skin types. A true bestseller at ₦3,500! 🧼"
    if any(w in m for w in ['price', 'cost', 'how much', 'naira']):
        listing = ', '.join(f"{p['name']} (₦{int(p['price']):,})" for p in products[:4])
        return f"Our range starts from ₦3,000. A few favourites: {listing}. Free shipping on orders over ₦80,000! 🚚"
    if any(w in m for w in ['ship', 'deliver', 'how long']):
        return "We offer local rider, interstate, air and international shipping. Local delivery is usually 1–3 days. You'll get a tracking code (NBR-…) and can follow your order in your account. 📦"
    if any(w in m for w in ['ingredient', 'natural', 'organic', 'chemical']):
        return "Everything we make is rooted in nature — shea butter, plantain ash, turmeric, rosehip and more. No harsh synthetics, ever. Is there a specific product you'd like the ingredients for?"
    if any(w in m for w in ['photo', 'picture', 'image', 'my skin', 'look at']):
        return "This looks interesting — let me get Regina's expert eyes on it. 💚 In the meantime, could you tell me a little about your skin type and main concern?"
    if any(w in m for w in ['loyal', 'point', 'reward', 'refer']):
        return "Every order earns loyalty points that unlock Bronze, Silver, Gold and Platinum perks — from free shipping to VIP gifts. You can also refer friends with your personal code in your account! 🎁"
    if any(w in m for w in ['thank', 'thanks', 'bye']):
        return "You're so welcome! 🌿 Treat yourself, stay healthy — and reach out any time. We're always here for you."
    return "Thank you for your message! 💚 I'd love to help — could you tell me a little more about your skin type or what you're hoping to achieve? For anything complex, I can connect you with Regina herself."


@app.route('/api/chat/send', methods=['POST'])
def chat():
    msg = request.get_json()['message']
    resp = assistant_reply(msg)
    db = get_db()
    db.execute('INSERT INTO chat_messages (user_id,message,is_assistant) VALUES (?,?,0)', (session.get('user_id'), msg))
    db.execute('INSERT INTO chat_messages (user_id,message,is_assistant) VALUES (?,?,1)', (session.get('user_id'), resp))
    db.commit()
    db.close()
    return jsonify({'success': True, 'response': resp})


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.context_processor
def inject_globals():
    is_admin = False
    if 'user_id' in session:
        db = get_db()
        u = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        db.close()
        is_admin = bool(u and u['is_admin'])
    return {'now_year': datetime.now().year, 'is_admin': is_admin,
            'paystack_public_key': conf('paystack_public', 'PAYSTACK_PUBLIC_KEY'),
            'site': get_settings()}


# --------------------------------------------------------------------------- #
#  Payments — Paystack
# --------------------------------------------------------------------------- #
def send_email(to_addr, subject, body):
    """Send a plain-text email via SMTP. Returns True on success, False if unconfigured/failed."""
    host = conf('smtp_host', 'SMTP_HOST')
    user = conf('smtp_user', 'SMTP_USER')
    pwd = conf('smtp_pass', 'SMTP_PASS')
    if not (host and user and pwd and to_addr):
        return False
    port = int(conf('smtp_port', 'SMTP_PORT', '587') or 587)
    from_addr = conf('smtp_from', 'SMTP_FROM') or user
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        print('[email] failed:', e)
        return False


def notify_email_addr():
    return conf('notify_email', 'NOTIFY_EMAIL') or conf('smtp_user', 'SMTP_USER')


def telegram_notify(text):
    """Send a message to the admin Telegram chat. Silent no-op if unconfigured."""
    token = conf('telegram_token', 'TELEGRAM_BOT_TOKEN')
    chat = conf('telegram_chat', 'TELEGRAM_CHAT_ID')
    if not (token and chat):
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text,
                                   'parse_mode': 'HTML'}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
        return True
    except Exception as e:
        print('[telegram] failed:', e)
        return False


def paystack_verify(reference):
    """Verify a transaction with Paystack. Returns (ok, data)."""
    secret = conf('paystack_secret', 'PAYSTACK_SECRET_KEY')
    if not secret:
        # No secret key configured — cannot verify server-side (test/dev mode).
        return None, {'message': 'Paystack not configured'}
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {secret}'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
        data = payload.get('data', {})
        return data.get('status') == 'success', data
    except (urllib.error.URLError, ValueError) as e:
        return False, {'message': str(e)}


@app.route('/api/paystack/config')
def paystack_config():
    pk = conf('paystack_public', 'PAYSTACK_PUBLIC_KEY')
    return jsonify({'public_key': pk, 'enabled': bool(pk)})


@app.route('/api/paystack/verify', methods=['POST'])
@login_required
def paystack_verify_route():
    reference = request.get_json().get('reference', '')
    ok, data = paystack_verify(reference)
    if ok is False:
        return jsonify({'success': False, 'error': data.get('message', 'Verification failed')}), 400
    # ok is True (verified) or None (not configured — accept in dev). Either way, allow order.
    return jsonify({'success': True, 'verified': bool(ok), 'reference': reference})


# --------------------------------------------------------------------------- #
#  Admin panel
# --------------------------------------------------------------------------- #
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        'revenue': db.execute("SELECT COALESCE(SUM(total),0) v FROM orders WHERE status != 'cancelled'").fetchone()['v'],
        'orders': db.execute('SELECT COUNT(*) v FROM orders').fetchone()['v'],
        'customers': db.execute('SELECT COUNT(*) v FROM users WHERE is_admin = 0').fetchone()['v'],
        'products': db.execute('SELECT COUNT(*) v FROM products').fetchone()['v'],
    }
    recent = db.execute('''SELECT o.*, u.first_name, u.last_name FROM orders o
                           LEFT JOIN users u ON o.user_id = u.id
                           ORDER BY o.created_at DESC LIMIT 6''').fetchall()
    top = db.execute('''SELECT p.name, p.image, COALESCE(SUM(oi.quantity),0) sold,
                        COALESCE(SUM(oi.quantity*oi.price),0) revenue
                        FROM products p LEFT JOIN order_items oi ON oi.product_id = p.id
                        GROUP BY p.id ORDER BY sold DESC LIMIT 5''').fetchall()
    low_stock = db.execute('SELECT * FROM products WHERE stock < 30 ORDER BY stock ASC LIMIT 5').fetchall()
    # simple 7-status order breakdown for the chart
    by_status = db.execute('SELECT status, COUNT(*) n FROM orders GROUP BY status').fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, recent=recent,
                           top=top, low_stock=low_stock, by_status=by_status)


@app.route('/admin/products')
@admin_required
def admin_products():
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY id').fetchall()
    db.close()
    return render_template('admin/products.html', products=products)


def all_categories():
    db = get_db()
    rows = db.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    db.close()
    base = ['soaps', 'moisturizers', 'serums', 'scrubs', 'masks', 'oils', 'lotions', 'bundles']
    cats = list(dict.fromkeys(base + [r['category'] for r in rows if r['category']]))
    return cats


@app.route('/admin/products/new')
@admin_required
def admin_product_new():
    return render_template('admin/product_form.html', product=None, categories=all_categories())


@app.route('/admin/products/<int:pid>/edit')
@admin_required
def admin_product_edit(pid):
    db = get_db()
    p = db.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
    db.close()
    if not p:
        abort(404)
    return render_template('admin/product_form.html', product=p, categories=all_categories())


@app.route('/api/admin/upload', methods=['POST'])
@admin_required
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        return jsonify({'success': False, 'error': 'Please upload a JPG, PNG, WEBP or GIF'}), 400
    folder = os.path.join('static', 'img')
    os.makedirs(folder, exist_ok=True)
    base = secure_filename(os.path.splitext(f.filename)[0]) or 'product'
    name = f"{base}-{random.randint(1000,9999)}{ext}"
    f.save(os.path.join(folder, name))
    return jsonify({'success': True, 'path': f'/static/img/{name}'})


@app.route('/api/admin/product/save', methods=['POST'])
@admin_required
def admin_product_save():
    d = request.get_json()
    slug = (d.get('slug') or d.get('name', '')).lower().strip().replace(' ', '-')
    fields = (d.get('name'), slug, d.get('description'), d.get('ingredients'),
              d.get('benefits'), float(d.get('price') or 0), d.get('image') or '🌿',
              d.get('category') or 'soaps', int(d.get('stock') or 0), d.get('badge') or None)
    db = get_db()
    try:
        if d.get('id'):
            db.execute('''UPDATE products SET name=?,slug=?,description=?,ingredients=?,benefits=?,
                          price=?,image=?,category=?,stock=?,badge=? WHERE id=?''', fields + (d['id'],))
        else:
            db.execute('''INSERT INTO products (name,slug,description,ingredients,benefits,price,image,category,stock,badge)
                          VALUES (?,?,?,?,?,?,?,?,?,?)''', fields)
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'success': False, 'error': 'A product with that name/slug already exists'}), 400
    db.close()
    return jsonify({'success': True})


@app.route('/api/admin/product/<int:pid>/delete', methods=['POST'])
@admin_required
def admin_product_delete(pid):
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (pid,))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/admin/orders')
@admin_required
def admin_orders():
    db = get_db()
    orders = db.execute('''SELECT o.*, u.first_name, u.last_name, u.email FROM orders o
                           LEFT JOIN users u ON o.user_id = u.id
                           ORDER BY o.created_at DESC''').fetchall()
    db.close()
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
    return render_template('admin/orders.html', orders=orders, statuses=statuses)


@app.route('/api/admin/order/status', methods=['POST'])
@admin_required
def admin_order_status():
    d = request.get_json()
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (d['status'], d['order_id']))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/admin/customers')
@admin_required
def admin_customers():
    db = get_db()
    customers = db.execute('''SELECT u.*, COUNT(o.id) order_count,
                              COALESCE(SUM(o.total),0) spent FROM users u
                              LEFT JOIN orders o ON o.user_id = u.id
                              WHERE u.is_admin = 0 GROUP BY u.id ORDER BY spent DESC''').fetchall()
    db.close()
    return render_template('admin/customers.html', customers=customers)


@app.route('/admin/chats')
@admin_required
def admin_chats():
    db = get_db()
    msgs = db.execute('''SELECT c.*, u.first_name FROM chat_messages c
                         LEFT JOIN users u ON c.user_id = u.id
                         ORDER BY c.created_at DESC LIMIT 200''').fetchall()
    db.close()
    return render_template('admin/chats.html', msgs=msgs)


@app.route('/admin/settings')
@admin_required
def admin_settings():
    return render_template('admin/settings.html', schema=SETTINGS_SCHEMA, settings=get_settings())


@app.route('/api/admin/settings/save', methods=['POST'])
@admin_required
def admin_settings_save():
    data = request.get_json()
    db = get_db()
    for key in DEFAULT_SETTINGS:
        if key in data:
            db.execute('''INSERT INTO settings (key, value) VALUES (?, ?)
                          ON CONFLICT(key) DO UPDATE SET value = excluded.value''',
                       (key, str(data[key])))
    db.commit()
    db.close()
    return jsonify({'success': True})


# --------------------------------------------------------------------------- #
#  Profile photo
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
#  Admin: Media library
# --------------------------------------------------------------------------- #
@app.route('/admin/media')
@admin_required
def admin_media():
    db = get_db()
    items = db.execute('SELECT * FROM media ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin/media.html', items=items)


@app.route('/api/admin/media/upload', methods=['POST'])
@admin_required
def admin_media_upload():
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    f = request.files['file']
    ext = os.path.splitext(f.filename)[1].lower()
    images = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    videos = ('.mp4', '.webm', '.mov', '.ogg')
    if ext in images:
        mtype = 'image'
    elif ext in videos:
        mtype = 'video'
    else:
        return jsonify({'success': False, 'error': 'Upload an image or video file'}), 400
    folder = os.path.join('static', 'media')
    os.makedirs(folder, exist_ok=True)
    base = secure_filename(os.path.splitext(f.filename)[0]) or mtype
    name = f"{base}-{random.randint(1000,9999)}{ext}"
    f.save(os.path.join(folder, name))
    path = f'/static/media/{name}'
    db = get_db()
    db.execute('INSERT INTO media (type, path, name) VALUES (?,?,?)', (mtype, path, f.filename))
    db.commit()
    db.close()
    return jsonify({'success': True, 'path': path, 'type': mtype})


@app.route('/api/admin/media/<int:mid>/delete', methods=['POST'])
@admin_required
def admin_media_delete(mid):
    db = get_db()
    row = db.execute('SELECT path FROM media WHERE id = ?', (mid,)).fetchone()
    if row:
        fp = os.path.join('.', row['path'].lstrip('/'))
        try:
            if os.path.exists(fp):
                os.remove(fp)
        except OSError as e:
            print('[media] delete failed:', e)
        db.execute('DELETE FROM media WHERE id = ?', (mid,))
        db.commit()
    db.close()
    return jsonify({'success': True})


# --------------------------------------------------------------------------- #
#  Admin: Testimonials
# --------------------------------------------------------------------------- #
@app.route('/admin/testimonials')
@admin_required
def admin_testimonials():
    db = get_db()
    items = db.execute('SELECT * FROM testimonials ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin/testimonials.html', items=items)


@app.route('/api/admin/testimonial/save', methods=['POST'])
@admin_required
def admin_testimonial_save():
    d = request.get_json()
    db = get_db()
    if d.get('id'):
        db.execute('UPDATE testimonials SET author=?, role=?, rating=?, comment=? WHERE id=?',
                   (d.get('author'), d.get('role'), float(d.get('rating') or 5), d.get('comment'), d['id']))
    else:
        db.execute('INSERT INTO testimonials (author, role, rating, comment) VALUES (?,?,?,?)',
                   (d.get('author'), d.get('role'), float(d.get('rating') or 5), d.get('comment')))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/admin/testimonial/<int:tid>/delete', methods=['POST'])
@admin_required
def admin_testimonial_delete(tid):
    db = get_db()
    db.execute('DELETE FROM testimonials WHERE id = ?', (tid,))
    db.commit()
    db.close()
    return jsonify({'success': True})


# --------------------------------------------------------------------------- #
#  Admin: Ad Studio (image -> video)
# --------------------------------------------------------------------------- #
@app.route('/admin/ads')
@admin_required
def admin_ads():
    provider = conf('video_provider', default='replicate')
    has_key = bool(conf('video_api_key'))
    db = get_db()
    clips = db.execute("SELECT * FROM media WHERE type='video' ORDER BY created_at DESC LIMIT 12").fetchall()
    products = db.execute('SELECT id, name, category, benefits, image FROM products ORDER BY name').fetchall()
    db.close()
    return render_template('admin/ads.html', provider=provider, has_key=has_key, clips=clips, products=products)


def _img_to_video(provider, api_key, model, image_url):
    """Call an image-to-video provider. Returns (ok, result_url_or_error)."""
    try:
        if provider == 'replicate':
            model_slug = model or 'stability-ai/stable-video-diffusion'
            req = urllib.request.Request(
                f'https://api.replicate.com/v1/models/{model_slug}/predictions',
                data=json.dumps({'input': {'input_image': image_url, 'cond_aug': 0.02}}).encode(),
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json',
                         'Prefer': 'wait'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode())
            out = data.get('output')
            url = out[-1] if isinstance(out, list) else out
            return (bool(url), url or data.get('status', 'processing'))
        elif provider == 'huggingface':
            model_slug = model or 'stabilityai/stable-video-diffusion-img2vid-xt'
            req = urllib.request.Request(
                f'https://api-inference.huggingface.co/models/{model_slug}',
                data=json.dumps({'inputs': image_url}).encode(),
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                return (True, r.read())  # raw video bytes
        elif provider == 'google':
            # Google Veo via the Gemini API (the engine behind Flow). Async: submit → poll → download.
            import time
            model_slug = model or 'veo-3.1-generate-preview'  # Veo 3.0 retires 2026-06-30
            if not image_url.startswith('data:'):
                return (False, 'For Google Veo, upload the photo here so it can be sent to the API.')
            header, b64 = image_url.split(',', 1)
            mime = header.split(';')[0].replace('data:', '') or 'image/jpeg'
            api = 'https://generativelanguage.googleapis.com/v1beta'
            body = {'instances': [{
                        'prompt': 'Cinematic product advertisement for a premium natural skincare brand, '
                                  'gentle camera push-in, soft studio lighting, elegant and clean.',
                        'image': {'bytesBase64Encoded': b64, 'mimeType': mime}}],
                    'parameters': {'aspectRatio': '16:9'}}
            req = urllib.request.Request(f'{api}/models/{model_slug}:predictLongRunning?key={api_key}',
                                         data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as r:
                op = json.loads(r.read().decode())
            op_name = op.get('name')
            if not op_name:
                return (False, 'Veo did not start: ' + json.dumps(op)[:200])
            for _ in range(40):  # poll up to ~4 minutes
                time.sleep(6)
                with urllib.request.urlopen(f'{api}/{op_name}?key={api_key}', timeout=30) as r:
                    st = json.loads(r.read().decode())
                if st.get('done'):
                    resp = st.get('response', {})
                    samples = (resp.get('generateVideoResponse', {}).get('generatedSamples')
                               or resp.get('generatedSamples') or [])
                    uri = samples[0].get('video', {}).get('uri') if samples else None
                    if uri:
                        dl = uri if 'key=' in uri else uri + ('&' if '?' in uri else '?') + 'key=' + api_key
                        with urllib.request.urlopen(dl, timeout=180) as r:
                            return (True, r.read())
                    return (False, 'Veo finished without a video: ' + json.dumps(st.get('error') or resp)[:200])
            return (False, 'Veo timed out — try again or check your Google Cloud quota.')
        else:
            return (False, f'Provider "{provider}" not recognised. Use replicate, huggingface or google.')
    except urllib.error.HTTPError as e:
        return (False, f'{provider} error {e.code}: {e.read().decode()[:200]}')
    except Exception as e:
        return (False, str(e))


@app.route('/api/admin/ad/generate', methods=['POST'])
@admin_required
def admin_ad_generate():
    provider = conf('video_provider', default='replicate')
    api_key = conf('video_api_key', 'VIDEO_API_KEY')
    model = conf('video_model')
    if not api_key:
        return jsonify({'success': False,
                        'error': f'No video API key set. Add your {provider} key in Site Settings → Ad Studio.'}), 400
    image_path = request.get_json().get('image_path', '')
    if not image_path:
        return jsonify({'success': False, 'error': 'Upload a product photo first'}), 400
    # Providers fetch the image remotely, so a localhost URL won't work — send a data URI instead.
    if image_path.startswith('http'):
        image_url = image_path
    else:
        import base64, mimetypes
        fp = os.path.join('.', image_path.lstrip('/'))
        if not os.path.exists(fp):
            return jsonify({'success': False, 'error': 'Image not found'}), 400
        mime = mimetypes.guess_type(fp)[0] or 'image/jpeg'
        with open(fp, 'rb') as fh:
            image_url = f"data:{mime};base64,{base64.b64encode(fh.read()).decode()}"
    ok, result = _img_to_video(provider, api_key, model, image_url)
    if not ok:
        return jsonify({'success': False, 'error': str(result)}), 400
    # If provider returned raw bytes (Hugging Face), save them; if a URL, store the URL.
    db = get_db()
    if isinstance(result, (bytes, bytearray)):
        folder = os.path.join('static', 'media')
        os.makedirs(folder, exist_ok=True)
        name = f"ad-{random.randint(10000,99999)}.mp4"
        with open(os.path.join(folder, name), 'wb') as fh:
            fh.write(result)
        path = f'/static/media/{name}'
    else:
        path = result
    db.execute('INSERT INTO media (type, path, name) VALUES (?,?,?)', ('video', path, 'AI ad clip'))
    db.commit()
    db.close()
    return jsonify({'success': True, 'path': path})


@app.route('/api/profile/photo', methods=['POST'])
@login_required
def profile_photo():
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    f = request.files['file']
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        return jsonify({'success': False, 'error': 'Please upload an image'}), 400
    folder = os.path.join('static', 'avatars')
    os.makedirs(folder, exist_ok=True)
    name = f"avatar-{session['user_id']}-{random.randint(1000,9999)}{ext}"
    f.save(os.path.join(folder, name))
    path = f'/static/avatars/{name}'
    db = get_db()
    db.execute('UPDATE users SET photo = ? WHERE id = ?', (path, session['user_id']))
    db.commit()
    db.close()
    return jsonify({'success': True, 'path': path})


if __name__ == '__main__':
    init_db()
    seed()
    app.run(debug=True, port=5000)
