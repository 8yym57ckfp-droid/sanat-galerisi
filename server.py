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
from datetime import date
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
          sold INTEGER NOT NULL DEFAULT 0, archived INTEGER NOT NULL DEFAULT 0,
          show_new INTEGER NOT NULL DEFAULT 0, show_collections INTEGER NOT NULL DEFAULT 0,
          show_curated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS custom_orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT, ref TEXT UNIQUE NOT NULL, image TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '', customer_name TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'new', offered_price INTEGER, offered_days INTEGER,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS product_likes (
          product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
          visitor_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(product_id, visitor_id)
        );
        """)
        order_columns = {row[1] for row in c.execute("PRAGMA table_info(custom_orders)")}
        for column, declaration in {
            "first_name": "TEXT NOT NULL DEFAULT ''", "last_name": "TEXT NOT NULL DEFAULT ''",
            "address": "TEXT NOT NULL DEFAULT ''", "city": "TEXT NOT NULL DEFAULT ''",
            "country": "TEXT NOT NULL DEFAULT ''", "postal_code": "TEXT NOT NULL DEFAULT ''",
            "counter_price": "INTEGER", "counter_note": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if column not in order_columns:
                c.execute(f"ALTER TABLE custom_orders ADD COLUMN {column} {declaration}")
        product_columns = {row[1] for row in c.execute("PRAGMA table_info(products)")}
        if "publish_at" not in product_columns:
            c.execute("ALTER TABLE products ADD COLUMN publish_at TEXT NOT NULL DEFAULT ''")
        if "show_new" not in product_columns:
            c.execute("ALTER TABLE products ADD COLUMN show_new INTEGER NOT NULL DEFAULT 0")
            c.execute("ALTER TABLE products ADD COLUMN show_collections INTEGER NOT NULL DEFAULT 0")
            c.execute("ALTER TABLE products ADD COLUMN show_curated INTEGER NOT NULL DEFAULT 0")
            c.execute("UPDATE products SET show_curated=featured")
            latest = c.execute("SELECT id FROM products WHERE archived=0 AND sold=0 ORDER BY id DESC LIMIT 4").fetchall()
            c.executemany("UPDATE products SET show_new=1 WHERE id=?", [(row[0],) for row in latest])
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
            c.execute("UPDATE products SET show_curated=featured")
            c.execute("UPDATE products SET show_new=1 WHERE id IN (SELECT id FROM products WHERE sold=0 ORDER BY id DESC LIMIT 4)")
        if not c.execute("SELECT 1 FROM settings WHERE key='product_sections_v2'").fetchone():
            c.execute("UPDATE products SET show_curated=0")
            c.execute("UPDATE products SET show_curated=1 WHERE id IN (SELECT id FROM products WHERE featured=1 AND sold=0 AND archived=0 ORDER BY id DESC LIMIT 3)")
            c.execute("INSERT INTO settings(key,value) VALUES('product_sections_v2','1')")


def settings():
    with connect() as c:
        return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def money(n):
    return f"₺{int(n or 0):,}".replace(",", ".")


def product_sections(product):
    choices = (("show_new", "Yeni Gelenler"), ("show_collections", "Koleksiyonlar"), ("show_curated", "Sanatçının Seçkisi"))
    return " · ".join(label for key, label in choices if product[key]) or "Seçilmedi"


def safe_url(value):
    v = (value or "").strip()
    return v if v.startswith(("https://", "http://")) else ""


def render(title, content, message=""):
    cfg = settings()
    nav = """<a href='/'>Ana Sayfa</a><a href='/#eserler'>Eserler</a><a href='/ozel-siparis'>Özel Sipariş</a><a href='/siparis-sorgula'>Sipariş Sorgula</a><a href='/arsiv'>Arşiv</a>"""
    alert = f"<div class='notice'>{esc(message)}</div>" if message else ""
    socials = "".join(f"<a target='_blank' rel='noopener' href='{esc(safe_url(cfg.get(k)))}'>{label}</a>" for k, label in (("instagram_url", "Instagram"), ("tiktok_url", "TikTok"), ("telegram_url", "Telegram")) if safe_url(cfg.get(k)))
    return f"""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='Perihan Baktaş el yapımı sanat eserleri ve kişiye özel siparişler.'><title>{esc(title)} · {esc(cfg.get('site_name'))}</title><link rel='stylesheet' href='/static/style.css'></head><body>
    <header class='site-head'><a class='brand' href='/'><span class='brand-mark'>✿</span><span><b>Sanat Atölyesi</b><small>EL YAPIMI TABLOLAR · {esc(cfg.get('site_name'))}</small></span></a><nav>{nav}</nav></header>
    {alert}<main>{content}</main><footer><div><b>{esc(cfg.get('site_name'))}</b><p>Bahar sizinle eve gelsin.</p></div><div class='socials'>{socials}</div></footer><script src='/static/app.js' defer></script></body></html>"""


def artwork(product):
    image = f"<img src='/{esc(product['image'])}' alt='{esc(product['title'])}'>" if product["image"] else f"<div class='art-placeholder art-{int(product['id']) % 5}' aria-hidden='true'><i>✿</i><i>✿</i><i>✿</i><i>✿</i></div>"
    old = f"<del>{money(product['price'])}</del>" if product["sale_price"] and product["sale_price"] < product["price"] else ""
    price = product["sale_price"] if product["sale_price"] and product["sale_price"] < product["price"] else product["price"]
    badge = "<span class='badge sold-badge'>Sahibini buldu</span>" if product["sold"] else ("<span class='badge'>Öne Çıkan</span>" if product["featured"] else "")
    buy_url = safe_url(product["whatsapp_url"]) or safe_url(settings().get("whatsapp_url"))
    buy = f"<a class='button small' href='{esc(buy_url)}' target='_blank' rel='noopener'>Bilgi Al</a>" if buy_url and not product["sold"] else ""
    like = f"<div class='like-row'><button type='button' class='like-button' data-like-code='{esc(product['code'])}' data-liked='0' aria-pressed='false' aria-label='0 beğeni'><svg viewBox='0 0 24 24' aria-hidden='true'><path d='M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z'/></svg><span class='like-count'>0</span></button></div>"
    return f"<article class='product-card'>{badge}<div class='art-frame'>{image}</div><div class='product-info'><span class='product-code'>{esc(product['code'])}</span><h3>{esc(product['title'])}</h3><p>{esc(product['size'])} · {esc(product['category'])}</p><p class='product-price'>{old}<b>{money(price)}</b></p><p class='description'>{esc(product['description'])}</p><div class='actions'>{buy}<a class='button ghost small' href='/ozel-siparis'>Benzerini İste</a></div>{like}</div></article>"


def product_cards(rows):
    return "".join(artwork(row) for row in rows) or "<p class='empty'>Bu bölümde henüz eser yok.</p>"


def render_legacy_home():
    """Keep the supplied homepage and continuously bind its artwork to the admin catalog."""
    return """<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Perihan Baktaş | Sanat Atölyesi</title><style>
    *{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}iframe{display:block;width:100%;height:100%;border:0;background:#fbf8f3}.quick-links{position:fixed;z-index:1000;right:18px;bottom:18px;display:flex;align-items:center;gap:7px;padding:8px;border:1px solid #eadfd6;border-radius:30px;background:#fffdf9ed;box-shadow:0 8px 28px #35261e24;backdrop-filter:blur(10px);font:600 12px Arial,sans-serif}.quick-links a{display:block;padding:9px 13px;border-radius:22px;color:#79546f;text-decoration:none;white-space:nowrap}.quick-links a:first-child{background:#486454;color:#fff}.quick-links a:hover{transform:translateY(-1px);background:#f4e9ed}.quick-links a:first-child:hover{background:#354d41}@media(max-width:600px){.quick-links{left:10px;right:10px;bottom:10px;justify-content:center;gap:2px}.quick-links a{font-size:11px;padding:9px 10px}}
    </style></head><body><iframe id='legacy-home' src='/legacy-homepage.html' title='Perihan Baktaş sanat galerisi'></iframe><nav class='quick-links' aria-label='Sipariş bağlantıları'><a href='/ozel-siparis'>Özel Sipariş Oluştur</a><a href='/siparis-sorgula'>Sipariş Sorgula</a></nav><script>
    (function(){var frame=document.getElementById('legacy-home'),busy=false,lastSignature='',filter={category:'',price:'',sort:'new'};
    var likeVisitor=(function(){var key='perihan-gallery-visitor';try{var id=localStorage.getItem(key);if(!id){id=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c==='x'?r:(r&3|8)).toString(16)});localStorage.setItem(key,id)}return id}catch(e){return 'session-'+Math.random().toString(16).slice(2)+Date.now().toString(16)}})();
    function setLikeState(d,code,value){window.__publicLikes=window.__publicLikes||{};window.__publicLikes[code]=value;Array.from(d.querySelectorAll('.like-button')).forEach(function(b){if(b.dataset.likeCode!==code)return;b.dataset.liked=value.liked?'1':'0';b.setAttribute('aria-pressed',value.liked?'true':'false');b.setAttribute('aria-label',value.count+' beğeni'+(value.liked?', beğendin':''));var n=b.querySelector('.like-count');if(n)n.textContent=value.count})}
    function ensureLikeRow(d,card,code){var ct=card.querySelector('.ct');if(!ct)return;var row=ct.querySelector('.like-row');if(!row){row=d.createElement('div');row.className='like-row';row.innerHTML='<button type=\"button\" class=\"like-button\" data-like-code=\"\" data-liked=\"0\" aria-pressed=\"false\" aria-label=\"0 beğeni\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z\"/></svg><span class=\"like-count\">0</span></button>';var actions=ct.querySelector('.card-actions');if(actions)actions.insertAdjacentElement('afterend',row);else ct.appendChild(row)}var b=row.querySelector('.like-button');b.dataset.likeCode=code;var state=(window.__publicLikes||{})[code]||{count:0,liked:false};setLikeState(d,code,state)}
    function install(d){if(d.getElementById('admin-live-catalog'))return;var style=d.getElementById('admin-catalog-sync');if(!style){style=d.createElement('style');style.id='admin-catalog-sync';style.textContent='del,s{color:#b9b1b5!important;opacity:.58!important}#admin-live-catalog{max-width:1160px;margin:42px auto 56px;padding:0 24px;text-align:center}#admin-live-catalog h2{font:700 30px Georgia,serif;color:#3f5a46;margin:0 0 8px}#admin-live-catalog .admin-catalog-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),250px));justify-content:center;gap:20px;margin-top:20px}.admin-filter-menu button{display:block;width:100%;border:0;background:transparent;text-align:left;cursor:pointer}#admin-live-catalog .card[hidden]{display:none!important}.editorial-section .editorial-grid,.editorial-section .curated-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),280px))!important;justify-content:center!important}.editorial-section .card{width:100%;max-width:280px;min-width:0;justify-self:center}#koleksiyonlar .collection-art-grid{max-width:1000px;margin:24px auto 0;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),280px));justify-content:center;gap:20px}#koleksiyonlar .collection-art-grid .card{width:100%;max-width:280px;min-width:0;justify-self:center}.like-row{display:flex;justify-content:flex-end;margin-top:5px}.like-button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:44px;padding:5px 8px;border:0;border-radius:999px;background:transparent;color:#927282;font:700 12px/1 Arial,sans-serif;cursor:pointer;transition:color .18s ease,background .18s ease,transform .18s ease}.like-button:hover{background:#fbf0f3;color:#d64f79;transform:translateY(-1px)}.like-button svg{width:19px;height:19px;fill:transparent;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;transition:fill .18s ease,transform .18s ease}.like-button[aria-pressed=true]{color:#df4f7b}.like-button[aria-pressed=true] svg{fill:currentColor;transform:scale(1.06)}.like-button:disabled{opacity:.62;cursor:wait}.like-button:focus-visible{outline:2px solid #b87b96;outline-offset:2px}@media(max-width:600px){#admin-live-catalog{padding:0 14px}}';d.head.appendChild(style)}
    var sold=d.querySelector('#sold-works-grid');if(!sold)return;
    var carouselStyle=d.getElementById('responsive-featured-carousel');if(!carouselStyle){carouselStyle=d.createElement('style');carouselStyle.id='responsive-featured-carousel';carouselStyle.textContent='.fw .ftt[data-loop-copies="1"]{animation:none!important;transform:none!important;width:100%!important;justify-content:center!important;flex-wrap:wrap!important}.fw.is-static .prev-default,.fw.is-static .next-default{display:none!important}.fw.is-manual .ftt{animation:none!important;transition:transform .65s ease!important}.all-works-section{max-width:1160px;margin:48px auto 60px;padding:30px 24px;background:#fffdf9;border:1px solid #efe4dd;border-radius:22px;box-shadow:0 12px 35px #5441370b}.all-works-filter{display:flex;align-items:center;justify-content:center;gap:10px;margin:0 auto 18px}.all-works-filter label{font-size:13px;color:#665c61}.all-works-filter select{min-width:220px;border:1px solid #e0d6d1;border-radius:999px;padding:10px 16px;background:#fff;color:#4b514e}.category-manager{border:1px solid #e8ddd7;border-radius:14px;padding:16px;margin:6px 0 18px}.category-manager legend,.size-choice legend,.category-checks legend{padding:0 8px;color:#4b514e;font-weight:700}.category-setting-row{display:flex;gap:9px;margin:8px 0}.category-setting-row input{flex:1;min-width:0}.size-choice{display:flex;align-items:end;gap:10px;border:1px solid #e8ddd7;border-radius:12px;padding:14px}.size-choice label{flex:1;display:grid;gap:6px}.size-choice input,.size-choice select{border:1px solid #e0d6d1;background:#fffdfb;border-radius:10px;padding:10px;width:100%}.size-x{padding-bottom:8px}.category-checks{display:flex;gap:16px;flex-wrap:wrap;border:1px solid #e8ddd7;border-radius:12px;padding:14px}.category-checks label{display:inline-flex;gap:7px;align-items:center}.phone-field{display:grid;grid-template-columns:minmax(170px,1fr) 1.2fr;gap:8px}.phone-field select,.phone-field input{min-width:0}.counteroffer-form{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;align-items:end;padding:14px;background:#f9f4ef;border-radius:12px}.counteroffer-form label{display:grid;gap:6px;font-size:12px}.counteroffer-form input{border:1px solid #e0d6d1;border-radius:9px;padding:10px}.counteroffer-box{padding:12px 14px;background:#fff4dd;border:1px solid #f0d89d;border-radius:12px;margin:12px 0}.counteroffer-box p{margin:4px 0}.badge.status-accepted{background:#e5f2e8;color:#2d7542}.badge.status-declined{background:#fbe6e7;color:#a33442}.badge.status-countered{background:#fff0cf;color:#94610b}.badge.status-new{background:#eaf1fb;color:#315f91}.badge.status-quoted{background:#eee8f6;color:#644b82}.code-input-row{display:flex;gap:8px}.code-input-row input{flex:1;min-width:0}.copy-code{border:0;border-radius:14px;background:#f6edf1;color:#704c67;font-size:11px;padding:5px 8px;cursor:pointer}.copy-code:hover{background:#ead9e2}@media(max-width:650px){.phone-field,.counteroffer-form{grid-template-columns:1fr}.size-choice{flex-wrap:wrap}.all-works-section{margin:28px 12px;padding:20px 12px}}';d.head.appendChild(carouselStyle)}
    var filterMenu=Array.from(d.querySelectorAll('details')).find(function(x){return (x.querySelector('summary')||{}).textContent.trim().startsWith('Kategori')}),oldControls=filterMenu&&filterMenu.parentElement&&filterMenu.parentElement.parentElement;if(oldControls){oldControls.classList.add('admin-filter-menu');var menus=oldControls.querySelectorAll('details');menus.forEach(function(menu,index){var label=index===0?'Kategori':index===1?'Fiyat':'Sırala',summary=menu.querySelector('summary'),list=menu.querySelector('div');if(summary)summary.dataset.menuLabel=label;if(list)list.dataset.menu=label.toLowerCase()})}
    var section=d.createElement('section');section.id='admin-live-catalog';section.className='all-works-section';section.innerHTML='<header class="section-heading"><span class="eyebrow">ATÖLYEDEN TÜM ÇALIŞMALAR</span><h2>Tüm Eserler</h2><p>Atölyedeki eserleri kategoriye göre keşfedin.</p></header><div class="all-works-filter"><label for="all-works-category">Kategori</label><select id="all-works-category"><option value="">Tüm kategoriler</option></select></div><div class="admin-catalog-grid"></div>';var curatedSection=d.querySelector('#sanatcinin-secimi');(curatedSection||sold).insertAdjacentElement('afterend',section);
    if(!d.__galleryLikesBound){d.__galleryLikesBound=true;d.addEventListener('click',function(e){var b=e.target.closest('.like-button');if(!b||b.disabled)return;e.preventDefault();var code=b.dataset.likeCode,liked=b.dataset.liked!=='1';b.disabled=true;fetch('/api/likes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,visitor:likeVisitor,liked:liked})}).then(function(r){if(!r.ok)throw Error('like');return r.json()}).then(function(result){setLikeState(d,result.code,result)}).catch(function(){b.disabled=false}).finally(function(){b.disabled=false})},true);fetch('/api/likes?visitor='+encodeURIComponent(likeVisitor),{cache:'no-store'}).then(function(r){if(!r.ok)throw Error('likes');return r.json()}).then(function(data){Object.keys(data.likes||{}).forEach(function(code){setLikeState(d,code,data.likes[code])})}).catch(function(){})}
    d.addEventListener('change',function(e){if(e.target&&e.target.id==='all-works-category'){filter.category=e.target.value;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map())}},true);d.addEventListener('click',function(e){var option=e.target.closest('.admin-filter-menu [data-filter-value]');if(option){e.preventDefault();var menu=option.closest('details'),label=menu&&menu.querySelector('summary');if(!label)return;var type=label.dataset.menuLabel;if(type==='Kategori')filter.category=option.dataset.filterValue;else if(type==='Fiyat')filter.price=option.dataset.filterValue;else filter.sort=option.dataset.filterValue;label.firstChild.nodeValue=option.textContent.trim()+' ';menu.open=false;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map());return}
    var arrow=e.target.closest('[data-featured-step]');if(arrow){e.preventDefault();e.stopImmediatePropagation();var track=d.querySelector('.fw .ftt'),cards=track&&track.querySelectorAll('.card');if(track&&cards&&cards.length){var copies=Math.max(1,Number(track.dataset.loopCopies)||1),count=Math.max(1,Math.floor(cards.length/copies));window.__adminSlide=((window.__adminSlide||0)+(Number(arrow.dataset.featuredStep)>0?1:-1)+count)%count;var root=track.closest('.fw');if(root)root.classList.add('is-manual');track.style.transition='transform .65s ease';track.style.transform='translateX(-'+(window.__adminSlide*(cards[0].getBoundingClientRect().width+24))+'px)'}}var tile=e.target.closest('.collection-tile[data-category]');if(tile){filter.category=tile.dataset.category;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map());d.querySelector('#admin-live-catalog').scrollIntoView({behavior:'smooth',block:'start'})}},true);
    }
    function cardTemplate(d,p){var all=Array.from(d.querySelectorAll('.card')),found=all.find(function(x){var chip=x.querySelector('.chip');return chip&&chip.textContent.trim()===p.code});return found||all[0]}
    function paint(d,card,p,cfg){card.hidden=false;card.dataset.productCode=p.code;var chip=card.querySelector('.chip');if(chip)chip.textContent=p.code;var title=card.querySelector('.ct .sf');if(title)title.textContent=p.title;var ct=card.querySelector('.ct');if(ct){var size=ct.querySelector('span:not(.pr)');if(size)size.textContent=p.size+(p.category?' · '+p.category:'');var price=ct.querySelector('.pr');if(price){price.replaceChildren();if(p.sale_price&&Number(p.sale_price)<Number(p.price)){var old=d.createElement('del');old.textContent=fmt(p.price);price.appendChild(old);price.appendChild(d.createTextNode(' '))}var current=d.createElement('b');current.textContent=fmt(p.sale_price&&Number(p.sale_price)<Number(p.price)?p.sale_price:p.price);price.appendChild(current)}var desc=ct.querySelector('.catalog-description');if(!desc){desc=d.createElement('span');desc.className='catalog-description';desc.style.cssText='display:block;margin:8px auto 12px;max-width:96%;color:#827783;font-size:11px;line-height:1.45;text-align:center;min-height:1.45em';var actions=ct.querySelector('.card-actions');ct.insertBefore(desc,actions||null)}desc.textContent=p.description||'';var actions=ct.querySelector('.card-actions');if(actions){actions.replaceChildren();if(p.sold){var sold=d.createElement('span');sold.className='btn g sold-tag';sold.textContent='Satıldı';actions.appendChild(sold)}else{var buy=d.createElement('a');buy.className='btn g';buy.href=p.whatsapp_url||cfg.whatsapp_url||'#iletisim';buy.textContent='Satın Al';if(buy.href.indexOf('http')===0){buy.target='_blank';buy.rel='noopener'}actions.appendChild(buy)}var inspect=d.createElement('button');inspect.type='button';inspect.className='btn inspect-btn';inspect.textContent='İncele';actions.appendChild(inspect)}}var art=card.querySelector('.art');if(art){if(p.image){var img=art.querySelector('