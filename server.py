#!/usr/bin/env python3
"""Perihan Baktaş art gallery and custom-order site (Python standard library only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import time
import uuid
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "site.sqlite3"
UPLOADS = ROOT / "uploads"
MAX_FILE = 8 * 1024 * 1024
MAX_REQUEST = MAX_FILE + 256 * 1024
ALLOWED_EXT = {".jpg", ".jpeg", ".jfif", ".png", ".webp"}
SEED = [
    ("TBL-001", "Baharın Şarkısı", "50x70 cm", 3200, 2500, "Çiçekler", "Pembe çiçekler ve yumuşak bahar tonları."),
    ("TBL-002", "Ayçiçekleri", "60x80 cm", 4000, 3200, "Çiçekler", "Sıcak sarı tonlarda ayçiçeği kompozisyonu."),
    ("TBL-003", "Sakin Kıyı", "70x90 cm", 5000, 4000, "Manzaralar", "Mavi ve kum tonlarında dingin bir kıyı."),
    ("TBL-004", "Kiraz Çiçekleri", "50x70 cm", 4500, 3500, "Çiçekler", "Bahar dallarından ilham alan özgün eser."),
    ("TBL-005", "Pembe Huzur", "40x60 cm", 3600, 2800, "Yumuşak Tonlar", "Lavanta ve pembe tonların huzurlu buluşması."),
    ("TBL-006", "Lavanta Tarlası", "50x70 cm", 3600, 3000, "Manzaralar", "Lavanta renklerinde sakin bir kır manzarası."),
    ("TBL-007", "Güneşli Sabah", "60x80 cm", 4500, 3800, "Manzaralar", "Güne yeni başlayan bir bahar manzarası."),
    ("TBL-008", "Gül Bahçesi", "40x50 cm", 2900, 2400, "Çiçekler", "Yumuşak pembe ve yeşil tonlarda güller."),
    ("TBL-009", "Kır Çiçekleri", "50x70 cm", 3100, 2700, "Çiçekler", "Renkli kır çiçeklerinden oluşan özgün çalışma."),
    ("TBL-010", "Bahar Dalı", "60x80 cm", 4600, 3900, "Çiçekler", "Çiçek açan dalların hareketli yorumu."),
    ("TBL-011", "Papatya Tarlası", "40x50 cm", 2600, 2200, "Çiçekler", "Açık tonlarda sade papatya kompozisyonu."),
    ("TBL-012", "Sabah Sisi", "70x90 cm", 5200, 4500, "Manzaralar", "Sakin bir sabahın yumuşak renkleri."),
    ("TBL-013", "Menekşe Bahçesi", "50x70 cm", 3700, 3100, "Çiçekler", "Mor ve yeşil tonların dengeli yorumu."),
    ("TBL-014", "Altın Ufuk", "60x80 cm", 4200, 3600, "Manzaralar", "Ufukta altın ışıkları taşıyan manzara."),
    ("TBL-015", "Pembe Göl", "40x60 cm", 3400, 2900, "Yumuşak Tonlar", "Göl yansımalarından ilham alan yumuşak tonlar."),
    ("TBL-016", "Ağaçların Fısıltısı", "70x70 cm", 4900, 4200, "Manzaralar", "Ağaçların dinginliğini taşıyan özgün eser."),
    ("TBL-017", "Yasemin Esintisi", "50x50 cm", 3000, 2500, "Çiçekler", "Açık renklerde zarif yasemin dalları."),
    ("TBL-018", "Gelincik Kırı", "60x90 cm", 4400, 3700, "Manzaralar", "Kırmızı gelinciklerin canlı renkleri."),
    ("TBL-019", "Erguvan Akşam", "50x70 cm", 3200, 3200, "Yumuşak Tonlar", "Akşam ışığında erguvan ve pembe tonlar."),
    ("TBL-020", "Lavanta Rüyası", "40x60 cm", 2800, 2800, "Yumuşak Tonlar", "Lavanta tonlarında dingin bir düş."),
    ("TBL-021", "Sessiz Mavi", "60x80 cm", 3500, 3500, "Manzaralar", "Mavinin sessiz ve sakin tonları."),
    ("TBL-022", "Yasemin Rüzgârı", "50x70 cm", 3800, 3300, "Çiçekler", "Yasemin dallarından ilham alan çalışma."),
    ("TBL-023", "Çınar Gölgesi", "60x80 cm", 4700, 4100, "Manzaralar", "Gölge ve ışıkla şekillenen bir manzara."),
    ("TBL-024", "Mor Salkım", "40x60 cm", 3000, 2600, "Çiçekler", "Mor salkımların bahar renkleri."),
    ("TBL-025", "Kırlangıç Yolu", "70x90 cm", 5500, 4800, "Manzaralar", "Geniş ufuklu, bahardan esinlenen manzara."),
    ("TBL-026", "Güneş Tarlası", "50x70 cm", 3900, 3400, "Manzaralar", "Güneş ışığını taşıyan sıcak renkler."),
    ("TBL-027", "Sessiz Limon", "40x50 cm", 2700, 2300, "Yumuşak Tonlar", "Sarı ve yeşilin sade buluşması."),
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY CHECK(id=1), password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products (
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
          size TEXT NOT NULL DEFAULT '', price INTEGER NOT NULL DEFAULT 0, sale_price INTEGER,
          category TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', image TEXT NOT NULL DEFAULT '',
          whatsapp_url TEXT NOT NULL DEFAULT '', featured INTEGER NOT NULL DEFAULT 0,
          sold INTEGER NOT NULL DEFAULT 0, archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS custom_orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT, ref TEXT UNIQUE NOT NULL, image TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '', customer_name TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'new', offered_price INTEGER, offered_days INTEGER,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        defaults = {
            "site_name": "Perihan Baktaş", "whatsapp_url": "", "instagram_url": "",
            "tiktok_url": "", "telegram_url": "", "categories": "Çiçekler, Manzaralar, Yumuşak Tonlar",
            "session_secret": secrets.token_hex(32),
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for i, item in enumerate(SEED):
                code, title, size, price, sale, category, desc = item
                sold = 1 if code in {"TBL-019", "TBL-020", "TBL-021"} else 0
                featured = 1 if i < 12 else 0
                c.execute("INSERT INTO products(code,title,size,price,sale_price,category,description,featured,sold) VALUES(?,?,?,?,?,?,?,?,?)",
                          (code, title, size, price, sale if sale < price else None, category, desc, featured, sold))


def settings():
    with connect() as c:
        return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def money(n):
    return f"₺{int(n or 0):,}".replace(",", ".")


def safe_url(value):
    v = (value or "").strip()
    return v if v.startswith(("https://", "http://")) else ""


def render(title, content, message=""):
    cfg = settings()
    nav = """<a href='/'>Ana Sayfa</a><a href='/#eserler'>Eserler</a><a href='/ozel-siparis'>Özel Sipariş</a><a href='/siparis-sorgula'>Sipariş Sorgula</a><a href='/arsiv'>Arşiv</a>"""
    alert = f"<div class='notice'>{esc(message)}</div>" if message else ""
    socials = "".join(f"<a target='_blank' rel='noopener' href='{esc(safe_url(cfg.get(k)))}'>{label}</a>" for k, label in (("instagram_url", "Instagram"), ("tiktok_url", "TikTok"), ("telegram_url", "Telegram")) if safe_url(cfg.get(k)))
    return f"""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='Perihan Baktaş el yapımı sanat eserleri ve kişiye özel siparişler.'><title>{esc(title)} · {esc(cfg.get('site_name'))}</title><link rel='stylesheet' href='/static/style.css'></head><body>
    <header class='site-head'><a class='brand' href='/'><span class='brand-mark'>✿</span><span><b>Sanat Atölyesi</b><small>EL YAPIMI TABLOLAR · {esc(cfg.get('site_name'))}</small></span></a><nav>{nav}<a class='admin-link' href='/admin'>Yönetim</a></nav></header>
    {alert}<main>{content}</main><footer><div><b>{esc(cfg.get('site_name'))}</b><p>Bahar sizinle eve gelsin.</p></div><div class='socials'>{socials}</div><a href='/admin'>Yönetim Paneli</a></footer><script src='/static/app.js' defer></script></body></html>"""


def artwork(product):
    image = f"<img src='/{esc(product['image'])}' alt='{esc(product['title'])}'>" if product["image"] else f"<div class='art-placeholder art-{int(product['id']) % 5}' aria-hidden='true'><i>✿</i><i>✿</i><i>✿</i><i>✿</i></div>"
    old = f"<del>{money(product['price'])}</del>" if product["sale_price"] and product["sale_price"] < product["price"] else ""
    price = product["sale_price"] if product["sale_price"] and product["sale_price"] < product["price"] else product["price"]
    badge = "<span class='badge sold-badge'>Sahibini buldu</span>" if product["sold"] else ("<span class='badge'>Öne Çıkan</span>" if product["featured"] else "")
    buy_url = safe_url(product["whatsapp_url"]) or safe_url(settings().get("whatsapp_url"))
    buy = f"<a class='button small' href='{esc(buy_url)}' target='_blank' rel='noopener'>Bilgi Al</a>" if buy_url and not product["sold"] else ""
    return f"<article class='product-card'>{badge}<div class='art-frame'>{image}</div><div class='product-info'><span class='product-code'>{esc(product['code'])}</span><h3>{esc(product['title'])}</h3><p>{esc(product['size'])} · {esc(product['category'])}</p><p class='product-price'>{old}<b>{money(price)}</b></p><p class='description'>{esc(product['description'])}</p><div class='actions'>{buy}<a class='button ghost small' href='/ozel-siparis'>Benzerini İste</a></div></div></article>"


def product_cards(rows):
    return "".join(artwork(row) for row in rows) or "<p class='empty'>Bu bölümde henüz eser yok.</p>"


def render_legacy_home():
    """Show the existing artwork homepage unchanged; expose new tools as a small overlay."""
    return """<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Perihan Baktaş | Sanat Atölyesi</title><style>
    *{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}iframe{display:block;width:100%;height:100%;border:0;background:#fbf8f3}.quick-links{position:fixed;z-index:1000;right:18px;bottom:18px;display:flex;align-items:center;gap:7px;padding:8px;border:1px solid #eadfd6;border-radius:30px;background:#fffdf9ed;box-shadow:0 8px 28px #35261e24;backdrop-filter:blur(10px);font:600 12px Arial,sans-serif}.quick-links a{display:block;padding:9px 13px;border-radius:22px;color:#79546f;text-decoration:none;white-space:nowrap}.quick-links a:first-child{background:#486454;color:#fff}.quick-links a:hover{transform:translateY(-1px);background:#f4e9ed}.quick-links a:first-child:hover{background:#354d41}@media(max-width:600px){.quick-links{left:10px;right:10px;bottom:10px;justify-content:center;gap:2px}.quick-links a{font-size:11px;padding:9px 10px}}
    </style></head><body><iframe id='legacy-home' src='/legacy-homepage.html' title='Perihan Baktaş sanat galerisi'></iframe><nav class='quick-links' aria-label='Sipariş bağlantıları'><a href='/ozel-siparis'>Özel Sipariş Oluştur</a><a href='/siparis-sorgula'>Sipariş Sorgula</a><a href='/admin'>Yönetim</a></nav><script>
    (function(){var frame=document.getElementById('legacy-home');function sync(){try{var d=frame.contentDocument;if(!d)return;fetch('/api/products',{cache:'no-store'}).then(function(r){return r.json()}).then(function(data){var products=data.products||[],byCode=new Map(products.map(function(p){return[p.code,p]}));function fmt(n){return '₺'+Number(n||0).toLocaleString('tr-TR')}
    function paint(card,p){if(!p||p.archived){card.hidden=true;return}card.hidden=false;var chip=card.querySelector('.chip');if(chip)chip.textContent=p.code;var title=card.querySelector('.ct .sf');if(title)title.textContent=p.title;var ct=card.querySelector('.ct');if(ct){var size=ct.querySelector('span:not(.pr)');if(size)size.textContent=p.size+(p.category?' · '+p.category:'');var price=ct.querySelector('.pr');if(price){price.replaceChildren();if(p.sale_price&&Number(p.sale_price)<Number(p.price)){var old=d.createElement('del');old.textContent=fmt(p.price);price.appendChild(old);price.appendChild(d.createTextNode(' '))}var current=d.createElement('b');current.textContent=fmt(p.sale_price&&Number(p.sale_price)<Number(p.price)?p.sale_price:p.price);price.appendChild(current)}var desc=ct.querySelector('.catalog-description');if(!desc){desc=d.createElement('span');desc.className='catalog-description';desc.style.cssText='display:block;margin-top:4px;color:#827783;font-size:11px;line-height:1.35';var actions=ct.querySelector('.card-actions');ct.insertBefore(desc,actions||null)}desc.textContent=p.description||'';var actions=ct.querySelector('.card-actions');if(actions){var inspect=actions.querySelector('.inspect-btn');if(p.sold){actions.replaceChildren();var sold=d.createElement('span');sold.className='btn g sold-tag';sold.textContent='Satıldı';actions.appendChild(sold)}else{actions.replaceChildren();var buy=d.createElement('a');buy.className='btn g';buy.href='#iletisim';buy.textContent='Satın Al';actions.appendChild(buy)}if(inspect){inspect.textContent='İncele';actions.appendChild(inspect)}else{var detail=d.createElement('button');detail.type='button';detail.className='btn inspect-btn';detail.textContent='İncele';actions.appendChild(detail)}}}var art=card.querySelector('.art');if(art&&p.image){var img=art.querySelector('img');if(!img){art.querySelectorAll('svg').forEach(function(x){x.remove()});img=d.createElement('img');img.style.cssText='position:absolute;inset:0;width:100%;height:100%;object-fit:cover';art.appendChild(img)}img.src='/'+p.image;img.alt=p.title}}
    var cards=Array.from(d.querySelectorAll('.card')),templates=new Map();cards.forEach(function(card){var chip=card.querySelector('.chip');if(chip&&!templates.has(chip.textContent.trim()))templates.set(chip.textContent.trim(),card);var p=chip&&byCode.get(chip.textContent.trim());if(p)paint(card,p);else card.hidden=true});
    var track=d.querySelector('.fw .ftt'),base=cards.find(function(x){return x.querySelector('.chip')});if(track&&base){var visible=products.filter(function(p){return !p.archived&&!p.sold}).sort(function(a,b){return Number(b.featured)-Number(a.featured)||a.id-b.id});var cycle=visible.concat(visible).map(function(p){var original=templates.get(p.code)||base;var clone=original.cloneNode(true);paint(clone,p);return clone});track.replaceChildren.apply(track,cycle)}
    var soldGrid=d.querySelector('.sold-works-grid'),soldBase=soldGrid&&soldGrid.querySelector('.card');if(soldGrid&&soldBase){var soldItems=products.filter(function(p){return !p.archived&&p.sold});var soldCards=soldItems.map(function(p){var clone=(templates.get(p.code)||soldBase).cloneNode(true);paint(clone,p);return clone});soldGrid.replaceChildren.apply(soldGrid,soldCards)}
    var cfg=data.settings||{};[['Instagram','instagram_url'],['TikTok','tiktok_url'],['Telegram','telegram_url'],['WhatsApp','whatsapp_url']].forEach(function(pair){if(!cfg[pair[1]])return;Array.from(d.querySelectorAll('a')).filter(function(a){return a.textContent.trim()===pair[0]||pair[0]==='WhatsApp'&&a.textContent.trim().indexOf('WhatsApp')===0}).forEach(function(a){a.href=cfg[pair[1]];a.target='_blank';a.rel='noopener'})})}).catch(function(){});}catch(e){}}
    frame.addEventListener('load',sync);if(frame.contentDocument&&frame.contentDocument.readyState==='complete')sync()})();
    </script></body></html>"""


def input_field(label, name, value="", kind="text", required=False, extra=""):
    req = " required" if required else ""
    if kind == "textarea":
        control = f"<textarea name='{name}' {req} {extra}>{esc(value)}</textarea>"
    else:
        control = f"<input name='{name}' type='{kind}' value='{esc(value)}' {req} {extra}>"
    return f"<label>{label}{control}</label>"


class SiteHandler(BaseHTTPRequestHandler):
    server_version = "SanatAtolyesi/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def send_html(self, body, status=200, headers=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        for k, v in headers or []:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, headers=None):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        for k, v in headers or []:
            self.send_header(k, v)
        self.end_headers()

    def static(self, urlpath):
        relative = urlpath.removeprefix("/static/")
        path = (ROOT / "static" / relative).resolve()
        if not path.is_relative_to((ROOT / "static").resolve()) or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def upload_file(self, fileitem, folder, prefix):
        if not fileitem or not fileitem["filename"]:
            return ""
        filename = Path(fileitem["filename"]).name
        ext = Path(filename).suffix.lower()
        data = fileitem["data"]
        if ext not in ALLOWED_EXT or not data or len(data) > MAX_FILE:
            raise ValueError("Görsel JPG, PNG veya WEBP olmalı ve 8 MB sınırını aşmamalı.")
        if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n") or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")):
            raise ValueError("Dosyanın içeriği geçerli bir JPG, PNG veya WEBP görseli değil.")
        name = prefix + uuid.uuid4().hex + ext
        target = UPLOADS / folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"uploads/{folder}/{name}"

    def parse_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST:
            raise ValueError("İstek boyutu çok büyük.")
        body = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")
        if ctype.lower().startswith("multipart/form-data"):
            message = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + ctype.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
            fields, files = {}, {}
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if not name:
                    continue
                payload = part.get_payload(decode=True) or b""
                filename = part.get_filename()
                if filename:
                    files[name] = {"filename": filename, "data": payload}
                else:
                    fields[name] = payload.decode("utf-8", "replace")
            return fields, files
        parsed = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
        return {k: v[-1] for k, v in parsed.items()}, {}

    def get_admin(self):
        raw = self.headers.get("Cookie", "")
        value = next((x.strip().split("=", 1)[1] for x in raw.split(";") if x.strip().startswith("gallery_admin=")), "")
        try:
            payload, sig = value.split(".", 1)
            secret = settings()["session_secret"]
            expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if hmac.compare_digest(sig, expected) and data.get("exp", 0) > time.time() and data.get("id") == 1:
                return data
        except Exception:
            pass
        return None

    def require_admin(self):
        data = self.get_admin()
        if data:
            return data
        self.redirect("/admin/login")
        return None

    def csrf_ok(self, fields):
        return bool(self.get_admin() and hmac.compare_digest(str(fields.get("csrf", "")), settings().get("csrf_token", "")))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/legacy-homepage.html":
            legacy = ROOT / "legacy-homepage.html"
            data = legacy.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/products":
            with connect() as c:
                items = [dict(r) for r in c.execute("SELECT * FROM products ORDER BY id")]
            cfg = settings()
            public_settings = {k: cfg.get(k, "") for k in ("site_name", "whatsapp_url", "instagram_url", "tiktok_url", "telegram_url", "categories")}
            payload = json.dumps({"products": items, "settings": public_settings}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path.startswith("/static/"):
            return self.static(path)
        if path.startswith("/uploads/"):
            relative = path.removeprefix("/")
            if relative.startswith("uploads/requests/") and not self.get_admin():
                return self.send_error(404)
            file = (ROOT / relative).resolve()
            if file.is_relative_to(UPLOADS.resolve()) and file.is_file():
                data = file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
                return
            return self.send_error(404)
        if path == "/":
            return self.send_html(render_legacy_home())
        if path == "/new-home":
            category = query.get("kategori", [""])[0]
            sort = query.get("sirala", [""])[0]
            with connect() as c:
                sql = "SELECT * FROM products WHERE archived=0 AND sold=0"
                args = []
                if category:
                    sql += " AND category=?"; args.append(category)
                order = "created_at DESC"
                if sort == "fiyat-artan": order = "COALESCE(sale_price,price) ASC"
                elif sort == "fiyat-azalan": order = "COALESCE(sale_price,price) DESC"
                rows = c.execute(sql + " ORDER BY featured DESC," + order, args).fetchall()
                featured = c.execute("SELECT * FROM products WHERE archived=0 AND sold=0 AND featured=1 ORDER BY id DESC LIMIT 8").fetchall()
                sold = c.execute("SELECT * FROM products WHERE archived=0 AND sold=1 ORDER BY id DESC").fetchall()
            cats = [x.strip() for x in settings().get("categories", "").split(",") if x.strip()]
            select = "".join(f"<option {'selected' if category == x else ''} value='{esc(x)}'>{esc(x)}</option>" for x in cats)
            hero = "<section class='hero'><div class='hero-copy'><span class='eyebrow'>EL YAPIMI · ÖZGÜN ESERLER</span><h1>Sanatla Dolu<br><em>Huzurlu Bir Bahar</em></h1><p>İlkbaharın sakinliği, fırçanın dokunuşuyla duvarınıza gelsin. Her eser kendine özgü bir renk ve hikâye taşır.</p><a class='button' href='#eserler'>Eserleri Keşfet</a><a class='button ghost' href='/ozel-siparis'>Özel Sipariş Oluştur</a></div><div class='hero-art'><div class='hero-canvas'><span>✿</span><span>✿</span><span>✿</span><span>✿</span></div><small>Perihan Baktaş · Atölyeden</small></div></section>"
            content = hero
            if featured:
                content += f"<section class='section'><div class='section-heading'><span class='eyebrow'>ATÖLYEDEN SEÇKİ</span><h2>Öne Çıkan Eserler</h2><p>Sanatın en özel parçalarını keşfedin.</p></div><div class='carousel'><button class='carousel-arrow' type='button' data-carousel='prev' aria-label='Önceki eserler'>‹</button><div class='product-grid carousel-track'>{product_cards(featured)}</div><button class='carousel-arrow' type='button' data-carousel='next' aria-label='Sonraki eserler'>›</button></div></section>"
            content += f"<section class='section' id='eserler'><div class='section-heading'><span class='eyebrow'>ÖZGÜN ÇALIŞMALAR</span><h2>Eser Koleksiyonu</h2><p>Size yakın renkleri ve manzaraları seçin.</p></div><form class='filters' method='get'><label>Kategori<select name='kategori'><option value=''>Tüm kategoriler</option>{select}</select></label><label>Sırala<select name='sirala'><option value=''>Öne çıkanlar</option><option value='fiyat-artan' {'selected' if sort=='fiyat-artan' else ''}>Fiyat: düşükten yükseğe</option><option value='fiyat-azalan' {'selected' if sort=='fiyat-azalan' else ''}>Fiyat: yüksekten düşüğe</option></select></label><button class='button small'>Uygula</button></form><div class='product-grid'>{product_cards(rows)}</div></section>"
            if sold:
                content += f"<section class='section sold-section'><div class='section-heading'><span class='eyebrow'>YENİ SAHİPLERİNE ULAŞTILAR</span><h2>Satılan Eserler</h2><p>Sahiplerine ulaşmış güzel parçalar.</p></div><div class='product-grid'>{product_cards(sold)}</div></section>"
            content += "<section class='custom-banner'><div><span class='eyebrow'>SİZE ÖZEL HAZIRLANSIN</span><h2>Aklınızdaki tabloyu<br>birlikte tasarlayalım.</h2><p>Referans görselinizi yükleyin, notunuzu ekleyin; size fiyat ve tahmini süreyle dönelim.</p><a class='button' href='/ozel-siparis'>Özel Sipariş Oluştur</a></div><img src='/static/siparis-ornek.jfif' alt='Özel sipariş için örnek referans görseli'></section>"
            content += "<section id='hakkimda' class='about'><span class='eyebrow'>ATÖLYEDEN BİR NOT</span><h2>Her Eserde Bir Bahar Hikâyesi</h2><p>Perihan Baktaş’ın el yapımı eserleri; çiçeklerin, doğanın ve mevsimlerin renklerinden ilham alır.</p></section>"
            return self.send_html(render("Ana Sayfa", content))
        if path == "/ozel-siparis":
            content = f"""<section class='page-intro'><span class='eyebrow'>SİZE ÖZEL HAZIRLANSIN</span><h1>Özel Sipariş Oluştur</h1><p>İstediğiniz eseri anlatan bir görsel yükleyin. Notunuzu ve iletişim bilginizi ekleyin; size fiyat ve tahmini süre teklifi hazırlayalım.</p></section><section class='form-layout'><div class='form-card'><form method='post' enctype='multipart/form-data' action='/ozel-siparis'><label>Referans görseli <input type='file' name='image' accept='.jpg,.jpeg,.jfif,.png,.webp' required><small>JPG, PNG veya WEBP · en fazla 8 MB</small></label><div class='image-preview' data-preview><span>Görsel önizlemesi</span><img alt='Yüklenen görsel önizlemesi'></div>{input_field('Notunuz (renk, ölçü, konu veya başka istekleriniz)', 'note', kind='textarea', extra="maxlength='2000' rows='5'")}{input_field('Adınız', 'customer_name', required=True, extra="maxlength='100'")}{input_field('Telefon veya e-posta', 'contact', required=True, extra="maxlength='120' placeholder='Sizinle nasıl iletişim kuralım?'")}<button class='button wide'>Sipariş Talebi Oluştur</button><small>Talebiniz yönetim paneline düşer. Teklif hazırlandığında referans kodunuzla sorgulayabilirsiniz.</small></form></div><aside class='reference-card'><img src='/static/siparis-ornek.jfif' alt='Örnek sipariş görseli'><span class='eyebrow'>ÖRNEK REFERANS</span><h2>Nasıl çalışır?</h2><ol><li>Görselinizi ve notunuzu gönderin.</li><li>Size özel fiyat ve süre teklifini bekleyin.</li><li>Referans kodunuzla teklifi görüntüleyip onaylayın.</li></ol></aside></section>"""
            return self.send_html(render("Özel Sipariş", content))
        if path == "/siparis-sorgula":
            ref = (query.get("kod", [""])[0] or "").upper().strip()
            content = "<section class='page-intro'><span class='eyebrow'>SİPARİŞİNİZİ TAKİP EDİN</span><h1>Sipariş Sorgula</h1><p>Talep oluştururken aldığınız referans kodunu girin.</p></section><section class='narrow form-card'><form method='get' action='/siparis-sorgula'><label>Sipariş referans kodu<input name='kod' value='" + esc(ref) + "' placeholder='PB-AB12CD' required></label><button class='button wide'>Siparişi Sorgula</button></form>"
            if ref:
                with connect() as c: order = c.execute("SELECT * FROM custom_orders WHERE ref=?", (ref,)).fetchone()
                if not order:
                    content += "<div class='notice error'>Bu kodla eşleşen bir sipariş bulunamadı. Kodu kontrol edip tekrar deneyin.</div>"
                else:
                    content += f"<div class='order-result'><span class='badge'>{esc(order['ref'])}</span><h2>{esc({'new':'Talebiniz alındı','quoted':'Teklifiniz hazır','accepted':'Siparişiniz onaylandı','declined':'Teklif reddedildi'}.get(order['status'],'Talep durumu'))}</h2><p>Durum: <b>{esc({'new':'İnceleniyor','quoted':'Onayınızı bekliyor','accepted':'Üretim sırasına alındı','declined':'Kapandı'}.get(order['status']))}</b></p><p>Talep tarihi: {esc(order['created_at'])}</p>"
                    if order["status"] == "quoted":
                        content += f"<div class='offer'><span>Teklif edilen fiyat</span><b>{money(order['offered_price'])}</b><span>Tahmini hazırlık süresi</span><b>{int(order['offered_days'])} gün</b></div><p>Teklifi kabul ettiğinizde siparişiniz üretim sırasına alınır.</p><form class='inline-form' method='post' action='/siparis-sorgula/{quote(ref)}/kabul'><button class='button'>Siparişi Oluşturmaya Devam Et</button></form><form class='inline-form' method='post' action='/siparis-sorgula/{quote(ref)}/reddet'><button class='button ghost'>Teklifi Reddet</button></form>"
                    elif order["status"] == "accepted":
                        wa = safe_url(settings().get("whatsapp_url"))
                        next_link = f"<a class='button' href='{esc(wa)}' target='_blank' rel='noopener'>Atölyeyle İletişime Geç</a>" if wa else "<p>Atölye sizinle paylaştığınız iletişim bilgisi üzerinden iletişime geçecektir.</p>"
                        content += f"<div class='offer'><span>Onaylanan fiyat</span><b>{money(order['offered_price'])}</b><span>Tahmini hazırlık süresi</span><b>{int(order['offered_days'])} gün</b></div><p>Siparişiniz oluşturulmaya devam ediyor.</p>{next_link}"
                    elif order["status"] == "new": content += "<p>Fiyat ve hazırlık süresi atölye tarafından belirlendiğinde burada görüntülenecek.</p>"
                    else: content += "<p>Yeni bir özel sipariş talebi oluşturabilirsiniz.</p>"
                    content += "</div>"
            content += "</section>"
            return self.send_html(render("Sipariş Sorgula", content))
        if path == "/arsiv":
            with connect() as c: rows = c.execute("SELECT * FROM products WHERE archived=1 ORDER BY created_at DESC").fetchall()
            content = f"<section class='page-intro'><span class='eyebrow'>ATÖLYE KAYITLARI</span><h1>Eser Arşivi</h1><p>Arşive alınan eserler bu listede saklanır.</p></section><div class='product-grid'>{product_cards(rows)}</div>"
            return self.send_html(render("Eser Arşivi", content))
        if path in ("/admin", "/admin/"):
            return self.redirect("/admin/orders" if self.get_admin() else "/admin/login")
        if path == "/admin/setup":
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            if exists: return self.redirect("/admin/login")
            content = "<section class='page-intro'><span class='eyebrow'>İLK KURULUM</span><h1>Yönetici Parolası Oluştur</h1><p>Bu panel yalnızca sizin belirleyeceğiniz parola ile açılır. En az 10 karakter kullanın.</p></section><section class='narrow form-card'><form method='post' action='/admin/setup'><label>Yeni parola<input type='password' name='password' minlength='10' required></label><label>Parolayı doğrula<input type='password' name='confirm' minlength='10' required></label><button class='button wide'>Yönetici Hesabı Oluştur</button></form></section>"
            return self.send_html(render("İlk Kurulum", content))
        if path == "/admin/login":
            content = "<section class='page-intro'><span class='eyebrow'>YÖNETİM PANELİ</span><h1>Yönetici Girişi</h1><p>Atölye yönetimine devam etmek için giriş yapın.</p></section><section class='narrow form-card'><form method='post' action='/admin/login'><label>Parola<input type='password' name='password' required autofocus></label><button class='button wide'>Giriş Yap</button></form></section>"
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            return self.send_html(render("Yönetici Girişi", content + ("" if exists else "<p class='center'><a href='/admin/setup'>İlk yönetici parolasını oluştur</a></p>")))
        if not path.startswith("/admin/"):
            return self.send_error(404)
        admin = self.require_admin()
        if not admin: return
        csrf = esc(admin["csrf"])
        if path == "/admin/logout":
            return self.redirect("/admin/login", [("Set-Cookie", "gallery_admin=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")])
        if path == "/admin/orders":
            with connect() as c: rows = c.execute("SELECT * FROM custom_orders ORDER BY CASE status WHEN 'new' THEN 0 WHEN 'quoted' THEN 1 ELSE 2 END,created_at DESC").fetchall()
            blocks = []
            for o in rows:
                status = {"new":"Yeni talep", "quoted":"Teklif bekliyor", "accepted":"Kabul edildi", "declined":"Reddedildi"}.get(o["status"],o["status"])
                photo = f"<a href='/{esc(o['image'])}' target='_blank'><img class='admin-thumb' src='/{esc(o['image'])}' alt='Sipariş görseli'></a>"
                quote_form = f"<form method='post' action='/admin/orders/{quote(o['ref'])}/quote' class='quote-form'><input type='hidden' name='csrf' value='{csrf}'><label>Fiyat (₺)<input type='number' min='1' name='price' value='{esc(o['offered_price'] or '')}' required></label><label>Süre (gün)<input type='number' min='1' name='days' value='{esc(o['offered_days'] or '')}' required></label><button class='button small'>Teklifi Kaydet / Güncelle</button></form>" if o["status"] not in ("accepted", "declined") else ""
                blocks.append(f"<article class='admin-order'>{photo}<div class='order-details'><div class='row-between'><span class='badge'>{esc(status)}</span><b>{esc(o['ref'])}</b></div><h3>{esc(o['customer_name'])}</h3><p>{esc(o['contact'])}</p><p>{esc(o['note']) or 'Not eklenmedi.'}</p><small>Oluşturulma: {esc(o['created_at'])}</small>{quote_form}</div></article>")
            content = f"<section class='admin-top'><div><span class='eyebrow'>YÖNETİM</span><h1>Özel Siparişler</h1><p>Yeni talepleri inceleyin, fiyat ve hazırlık süresi tanımlayın.</p></div>{admin_nav('orders')}</section><div class='admin-orders'>{''.join(blocks) or '<p class=empty>Henüz özel sipariş yok.</p>'}</div>"
            return self.send_html(render("Yönetim · Siparişler", content))
        if path == "/admin/products":
            with connect() as c: rows = c.execute("SELECT * FROM products WHERE archived=0 ORDER BY featured DESC,id").fetchall()
            listing = "".join(f"<tr><td>{esc(p['code'])}</td><td>{esc(p['title'])}</td><td>{esc(p['size'])}</td><td>{esc(p['category'])}</td><td>{money(p['sale_price'] or p['price'])}</td><td>{'Evet' if p['featured'] else '—'}</td><td><a href='/admin/products/{p['id']}'>Düzenle</a> · <form class='inline-form' method='post' action='/admin/products/{p['id']}/archive'><input type='hidden' name='csrf' value='{csrf}'><button class='text-button'>Arşivle</button></form></td></tr>" for p in rows)
            content = f"<section class='admin-top'><div><span class='eyebrow'>KATALOG</span><h1>Tablolar</h1><p>Fiyat, ölçü, kategori, açıklama ve öne çıkarma ayarları.</p></div>{admin_nav('products')}</section><p><a class='button small' href='/admin/products/new'>+ Yeni Tablo Ekle</a></p><div class='table-wrap'><table><thead><tr><th>Kod</th><th>Eser</th><th>Ölçü</th><th>Kategori</th><th>Fiyat</th><th>Öne çıkan</th><th>İşlem</th></tr></thead><tbody>{listing}</tbody></table></div><h2>Arşiv</h2><p><a href='/arsiv'>Arşivdeki eserleri görüntüle</a></p>"
            return self.send_html(render("Yönetim · Tablolar", content))
        if path == "/admin/products/new" or re.fullmatch(r"/admin/products/\d+", path):
            product = None
            if path != "/admin/products/new":
                with connect() as c: product = c.execute("SELECT * FROM products WHERE id=?", (int(path.rsplit('/',1)[-1]),)).fetchone()
                if not product: return self.send_error(404)
            val = lambda key, default="": product[key] if product else default
            featured = "checked" if product and product["featured"] else ""
            sold = "checked" if product and product["sold"] else ""
            content = f"<section class='admin-top'><div><span class='eyebrow'>KATALOG</span><h1>{'Tabloyu Düzenle' if product else 'Yeni Tablo Ekle'}</h1></div>{admin_nav('products')}</section><section class='form-card admin-form'><form method='post' enctype='multipart/form-data' action='/admin/products/save'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='id' value='{esc(val('id'))}'><div class='form-grid'>{input_field('Eser kodu', 'code', val('code'), required=True)}{input_field('Eser adı', 'title', val('title'), required=True)}{input_field('Ölçü (örn. 50x70 cm)', 'size', val('size'), required=True)}{input_field('Kategori', 'category', val('category'), required=True)}{input_field('Liste fiyatı (₺)', 'price', val('price'), 'number', True, "min='0'")}{input_field('İndirimli fiyat (₺, isteğe bağlı)', 'sale_price', val('sale_price') or '', 'number', False, "min='0'")}{input_field('WhatsApp bağlantısı (isteğe bağlı)', 'whatsapp_url', val('whatsapp_url'), 'url', False, "placeholder='https://wa.me/...' class='span-2'")}{input_field('Açıklama', 'description', val('description'), 'textarea', False, "rows='4' class='span-2'")}<label class='span-2'>Eser görseli<input type='file' name='image' accept='.jpg,.jpeg,.jfif,.png,.webp'><small>JPG, PNG veya WEBP · en fazla 8 MB{(' · Mevcut görsel: '+esc(val('image'))) if product and val('image') else ''}</small></label></div><div class='check-row'><label><input type='checkbox' name='featured' value='1' {featured}> Öne çıkanlarda göster</label><label><input type='checkbox' name='sold' value='1' {sold}> Satıldı olarak göster</label></div><button class='button'>Kaydet</button> <a class='button ghost' href='/admin/products'>İptal</a></form></section>"
            return self.send_html(render("Yönetim · Tablo", content))
        if path == "/admin/settings":
            cfg = settings()
            content = f"<section class='admin-top'><div><span class='eyebrow'>SİTE AYARLARI</span><h1>Bağlantılar ve Kategoriler</h1><p>WhatsApp ve sosyal medya bağlantılarını, kategori listesini yönetin.</p></div>{admin_nav('settings')}</section><section class='narrow form-card'><form method='post' action='/admin/settings'><input type='hidden' name='csrf' value='{csrf}'>{input_field('Atölye adı', 'site_name', cfg.get('site_name'), required=True)}{input_field('WhatsApp bağlantısı', 'whatsapp_url', cfg.get('whatsapp_url'), 'url', False, "placeholder='https://wa.me/905...' ")}{input_field('Instagram URL', 'instagram_url', cfg.get('instagram_url'), 'url')}{input_field('TikTok URL', 'tiktok_url', cfg.get('tiktok_url'), 'url')}{input_field('Telegram URL', 'telegram_url', cfg.get('telegram_url'), 'url')}{input_field('Kategoriler (virgülle ayırın)', 'categories', cfg.get('categories'), 'textarea', False, "rows='3'")}<button class='button wide'>Ayarları Kaydet</button></form></section>"
            return self.send_html(render("Yönetim · Ayarlar", content))
        return self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            fields, files = self.parse_form()
        except ValueError as e:
            return self.send_html(render("İstek Hatası", f"<section class='narrow form-card'><h1>İşlem tamamlanamadı</h1><p>{esc(e)}</p><a href='/'>Ana sayfaya dön</a></section>"), 400)
        if path == "/admin/setup":
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            pw = fields.get("password", "")
            if exists: return self.redirect("/admin/login")
            if len(pw) < 10 or pw != fields.get("confirm"):
                return self.send_html(render("İlk Kurulum", "<section class='narrow form-card'><h1>Parolalar eşleşmiyor</h1><p>En az 10 karakterli, aynı parolayı tekrar girin.</p><a href='/admin/setup'>Geri dön</a></section>"), 400)
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 310000)
            stored = base64.b64encode(salt + digest).decode()
            with connect() as c: c.execute("INSERT INTO admin(id,password_hash) VALUES(1,?)", (stored,))
            return self.redirect("/admin/login")
        if path == "/admin/login":
            with connect() as c: row = c.execute("SELECT password_hash FROM admin WHERE id=1").fetchone()
            if row:
                try:
                    raw = base64.b64decode(row["password_hash"])
                    digest = hashlib.pbkdf2_hmac("sha256", fields.get("password", "").encode(), raw[:16], 310000)
                    if hmac.compare_digest(raw[16:], digest):
                        csrf = secrets.token_urlsafe(24)
                        with connect() as c: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('csrf_token',?)", (csrf,))
                        payload = base64.urlsafe_b64encode(json.dumps({"id":1,"csrf":csrf,"exp":time.time()+86400*7}).encode()).decode().rstrip("=")
                        sig = hmac.new(settings()["session_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
                        return self.redirect("/admin/orders", [("Set-Cookie", f"gallery_admin={payload}.{sig}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800")])
                except Exception: pass
            return self.send_html(render("Giriş Hatası", "<section class='narrow form-card'><h1>Parola hatalı</h1><p>Yönetici parolasını kontrol edip yeniden deneyin.</p><a href='/admin/login'>Geri dön</a></section>"), 401)
        if path == "/ozel-siparis":
            try:
                img = self.upload_file(files.get("image"), "requests", "request-")
                if not img: raise ValueError("Bir referans görseli seçin.")
                note = fields.get("note", "").strip()[:2000]
                name = fields.get("customer_name", "").strip()[:100]
                contact = fields.get("contact", "").strip()[:120]
                if not name or not contact: raise ValueError("Ad ve iletişim bilgisi gerekli.")
                ref = "PB-" + secrets.token_hex(4).upper()
                with connect() as c:
                    while c.execute("SELECT 1 FROM custom_orders WHERE ref=?", (ref,)).fetchone(): ref = "PB-" + secrets.token_hex(4).upper()
                    c.execute("INSERT INTO custom_orders(ref,image,note,customer_name,contact) VALUES(?,?,?,?,?)", (ref,img,note,name,contact))
                content = f"<section class='page-intro'><span class='eyebrow'>TALEBİNİZ ALINDI</span><h1>Özel sipariş talebiniz oluşturuldu</h1><p>Bu referans kodunu saklayın. Fiyat ve tahmini süre hazırlandığında kodunuzla sorgulayabilirsiniz.</p></section><section class='narrow form-card center'><span class='reference-code'>{esc(ref)}</span><p>Referans kodunuz</p><a class='button' href='/siparis-sorgula?kod={quote(ref)}'>Siparişimi Sorgula</a></section>"
                return self.send_html(render("Talep Oluşturuldu", content))
            except ValueError as e:
                return self.send_html(render("Özel Sipariş", f"<section class='narrow form-card'><h1>Talep oluşturulamadı</h1><p>{esc(e)}</p><a href='/ozel-siparis'>Geri dön</a></section>"), 400)
        if path.startswith("/siparis-sorgula/") and path.endswith(("/kabul", "/reddet")):
            action = path.rsplit("/", 1)[-1]
            ref = path.split("/")[-2].upper()
            with connect() as c:
                row = c.execute("SELECT * FROM custom_orders WHERE ref=?", (ref,)).fetchone()
                if row and row["status"] == "quoted":
                    status = "accepted" if action == "kabul" else "declined"
                    c.execute("UPDATE custom_orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE ref=?", (status, ref))
            return self.redirect("/siparis-sorgula?kod=" + quote(ref))
        if path.startswith("/admin/"):
            admin = self.get_admin()
            if not admin: return self.redirect("/admin/login")
            if not self.csrf_ok(fields): return self.send_error(403, "İstek doğrulanamadı. Sayfayı yenileyip tekrar deneyin.")
        if path.startswith("/admin/orders/") and path.endswith("/quote"):
            ref = path.split("/")[-2].upper()
            try: price, days = int(fields.get("price", "")), int(fields.get("days", ""))
            except ValueError: return self.send_error(400, "Fiyat ve süre sayı olmalı.")
            if price < 1 or days < 1: return self.send_error(400, "Fiyat ve süre pozitif olmalı.")
            with connect() as c: c.execute("UPDATE custom_orders SET status='quoted',offered_price=?,offered_days=?,updated_at=CURRENT_TIMESTAMP WHERE ref=? AND status IN ('new','quoted')", (price, days, ref))
            return self.redirect("/admin/orders")
        if path == "/admin/products/save":
            try:
                pid = int(fields.get("id") or 0)
                code = fields.get("code", "").strip().upper()[:30]
                title = fields.get("title", "").strip()[:120]
                size = fields.get("size", "").strip()[:60]
                category = fields.get("category", "").strip()[:80]
                price = int(fields.get("price", "0"))
                sale = int(fields.get("sale_price")) if fields.get("sale_price", "").strip() else None
                desc = fields.get("description", "").strip()[:1500]
                wa = safe_url(fields.get("whatsapp_url", ""))
                if not code or not title or not size or not category or price < 0: raise ValueError("Kod, ad, ölçü, kategori ve geçerli bir fiyat girin.")
                image = self.upload_file(files.get("image"), "works", "work-")
                featured, sold = int(fields.get("featured") == "1"), int(fields.get("sold") == "1")
                with connect() as c:
                    if pid:
                        old = c.execute("SELECT image FROM products WHERE id=?", (pid,)).fetchone()
                        if not old: return self.send_error(404)
                        image = image or old["image"]
                        c.execute("UPDATE products SET code=?,title=?,size=?,price=?,sale_price=?,category=?,description=?,image=?,whatsapp_url=?,featured=?,sold=? WHERE id=?", (code,title,size,price,sale,category,desc,image,wa,featured,sold,pid))
                    else:
                        c.execute("INSERT INTO products(code,title,size,price,sale_price,category,description,image,whatsapp_url,featured,sold) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (code,title,size,price,sale,category,desc,image,wa,featured,sold))
                return self.redirect("/admin/products")
            except (ValueError, sqlite3.IntegrityError) as e:
                return self.send_html(render("Tablo Kaydedilemedi", f"<section class='narrow form-card'><h1>Tablo kaydedilemedi</h1><p>{esc(e) or 'Eser kodu başka bir tabloda kullanılıyor.'}</p><a href='/admin/products'>Tablolara dön</a></section>"), 400)
        archive = re.fullmatch(r"/admin/products/(\d+)/archive", path)
        if archive:
            with connect() as c: c.execute("UPDATE products SET archived=1 WHERE id=?", (int(archive.group(1)),))
            return self.redirect("/admin/products")
        if path == "/admin/settings":
            allowed = ("site_name", "whatsapp_url", "instagram_url", "tiktok_url", "telegram_url")
            with connect() as c:
                for key in allowed:
                    val = fields.get(key, "").strip()
                    if key.endswith("_url"): val = safe_url(val)
                    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key,val[:500]))
                categories = ", ".join(dict.fromkeys(x.strip()[:80] for x in fields.get("categories", "").split(",") if x.strip()))
                c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('categories',?)", (categories,))
            return self.redirect("/admin/settings")
        return self.send_error(404)


def admin_nav(active):
    links = (("orders", "Özel Siparişler", "/admin/orders"), ("products", "Tablolar", "/admin/products"), ("settings", "Site Ayarları", "/admin/settings"))
    return "<nav class='admin-nav'>" + "".join(f"<a class='{'active' if key==active else ''}' href='{url}'>{label}</a>" for key,label,url in links) + "<a href='/admin/logout'>Çıkış</a></nav>"


if __name__ == "__main__":
    init_db()
    host = os.environ.get("GALLERY_HOST", "127.0.0.1")
    port = int(os.environ.get("GALLERY_PORT", "8000"))
    print(f"Sanat Atölyesi is running at http://{host}:{port}")
    print("First visit: /admin/setup to create the administrator password.")
    ThreadingHTTPServer((host, port), SiteHandler).serve_forever()
