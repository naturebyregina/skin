# Nature by Regina

Luxury natural skincare e-commerce platform — *"…Treat yourself, stay healthy."*

A Flask web app with a full storefront and an admin control panel.

## Features

**Storefront**
- Animated, mobile-first design (green / beige / gold) with real product photos
- Shop with category filters & sorting, rich product pages, reviews & ratings
- Cart, multi-step checkout, order tracking timeline
- Customer accounts: profile photo, loyalty tiers & points, wishlist, order history
- Blog/Journal, About, Contact (with Google Calendar consultation booking), FAQ
- "Regina's Team" AI chat assistant, newsletter

**Admin panel** (`/admin`)
- Dashboard analytics, product CRUD (with image upload & custom categories)
- Orders with status updates & payment-receipt review
- Customers, testimonials manager, chat logs
- **Media Library** — host & delete images/videos
- **Ad Studio** — image-to-video (Replicate / Hugging Face / Google Veo) + free-tool links + ad prompt generator
- **Site Settings (Developer Mode)** — edit logo, hero/story images, homepage video, brand text, hero, multiple bank accounts, contact info, social links, theme colours, and all API keys (Paystack, SMTP email, Telegram, video)

**Integrations** (all optional, configured in Site Settings)
- Paystack card payments, bank transfer with receipt upload, pay-on-delivery
- Email confirmations (SMTP), Telegram order alerts, Google Calendar links

## Run locally

Windows: double-click `run.bat`.

Or manually:

```bash
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

## Admin access

- URL: `/login` then go to `/admin`
- Email: `admin@naturebyregina.com`
- Password: `admin123`  *(change this before going live — set `ADMIN_PASSWORD`)*

## Tech

Flask · SQLite · vanilla JS · HTML/CSS. No build step required.
