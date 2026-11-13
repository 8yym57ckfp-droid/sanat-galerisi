#!/usr/bin/env python3
"""Perihan Baktaş art gallery site (Python standard library only)."""
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
from datetime import date, datetime
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

ROOT = Path(__file__).resolve().parent
DATA_ROOT = Path(os.environ.get("GALLERY_DATA_DIR", str(ROOT))).expanduser()
DB_PATH = DATA_ROOT / "data" / "site.sqlite3"
UPLOADS = DATA_ROOT / "uploads"
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
        CREATE TABLE IF NOT EXISTS product_likes (
          product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
          visitor_id TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(product_id, visitor_id)
        );
        """)
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
    nav = """<a href='/'>Ana Sayfa</a><a href='/#eserler'>Eserler</a><a href='/arsiv'>Arşiv</a>"""
    alert = f"<div class='notice'>{esc(message)}</div>" if message else ""
    socials = "".join(f"<a target='_blank' rel='noopener' href='{esc(safe_url(cfg.get(k)))}'>{label}</a>" for k, label in (("instagram_url", "Instagram"), ("tiktok_url", "TikTok"), ("telegram_url", "Telegram")) if safe_url(cfg.get(k)))
    return f"""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='Perihan Baktaş el yapımı sanat eserleri.'><title>{esc(title)} · {esc(cfg.get('site_name'))}</title><link rel='stylesheet' href='/static/style.css'></head><body>
    <header class='site-head'><a class='brand' href='/'><span class='brand-mark'>✿</span><span><b>Sanat Atölyesi</b><small>EL YAPIMI TABLOLAR · {esc(cfg.get('site_name'))}</small></span></a><nav>{nav}</nav></header>
    {alert}<main>{content}</main><footer><div><b>{esc(cfg.get('site_name'))}</b><p>Bahar sizinle eve gelsin.</p></div><div class='socials'>{socials}</div></footer><script src='/static/app.js' defer></script></body></html>"""


def artwork(product):
    image = f"<img src='/{esc(product['image'])}' alt='{esc(product['title'])}'>" if product["image"] else f"<div class='art-placeholder art-{int(product['id']) % 5}' aria-hidden='true'><i>✿</i><i>✿</i><i>✿</i><i>✿</i></div>"
    old = f"<del>{money(product['price'])}</del>" if product["sale_price"] and product["sale_price"] < product["price"] else ""
    price = product["sale_price"] if product["sale_price"] and product["sale_price"] < product["price"] else product["price"]
    badge = "<span class='badge sold-badge'>Sahibini buldu</span>" if product["sold"] else ("<span class='badge'>Öne Çıkan</span>" if product["featured"] else "")
    buy_url = safe_url(product["whatsapp_url"]) or safe_url(settings().get("whatsapp_url"))
    buy = (f"<a class='button small' href='{esc(buy_url)}' target='_blank' rel='noopener'>Bilgi Al</a>" if buy_url and not product["sold"] else ("<span class='button small sold-button' aria-disabled='true'>Satıldı</span>" if product["sold"] else ""))
    like = f"<div class='like-row'><button type='button' class='like-button' data-like-code='{esc(product['code'])}' data-liked='0' aria-pressed='false' aria-label='0 beğeni'><svg viewBox='0 0 24 24' aria-hidden='true'><path d='M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z'/></svg><span class='like-count'>0</span></button></div>"
    return f"<article class='product-card'>{badge}<div class='art-frame'>{image}</div><div class='product-info'><span class='product-code'>{esc(product['code'])}</span><h3>{esc(product['title'])}</h3><p>{esc(product['size'])} · {esc(product['category'])}</p><p class='product-price'>{old}<b>{money(price)}</b></p><p class='description'>{esc(product['description'])}</p><div class='actions'>{buy}</div>{like}</div></article>"


def product_cards(rows):
    return "".join(artwork(row) for row in rows) or "<p class='empty'>Bu bölümde henüz eser yok.</p>"


def render_legacy_home():
    """Keep the supplied homepage and continuously bind its artwork to the admin catalog."""
    return """<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Perihan Baktaş | Sanat Atölyesi</title><style>
    *{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}iframe{display:block;width:100%;height:100%;border:0;background:#fbf8f3}
    </style></head><body><iframe id='legacy-home' src='/legacy-homepage.html' title='Perihan Baktaş sanat galerisi'></iframe><script>
    (function(){var frame=document.getElementById('legacy-home'),busy=false,lastSignature='',filter={category:'',price:'',sort:'new'};
    var likeVisitor=(function(){var key='perihan-gallery-visitor';try{var id=localStorage.getItem(key);if(!id){id=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0;return(c==='x'?r:(r&3|8)).toString(16)});localStorage.setItem(key,id)}return id}catch(e){return 'session-'+Math.random().toString(16).slice(2)+Date.now().toString(16)}})();
    function setLikeState(d,code,value){window.__publicLikes=window.__publicLikes||{};window.__publicLikes[code]=value;Array.from(d.querySelectorAll('.like-button')).forEach(function(b){if(b.dataset.likeCode!==code)return;b.dataset.liked=value.liked?'1':'0';b.setAttribute('aria-pressed',value.liked?'true':'false');b.setAttribute('aria-label',value.count+' beğeni'+(value.liked?', beğendin':''));var n=b.querySelector('.like-count');if(n)n.textContent=value.count})}
    function ensureLikeRow(d,card,code){var ct=card.querySelector('.ct');if(!ct)return;var row=ct.querySelector('.like-row');if(!row){row=d.createElement('div');row.className='like-row';row.innerHTML='<button type=\"button\" class=\"like-button\" data-like-code=\"\" data-liked=\"0\" aria-pressed=\"false\" aria-label=\"0 beğeni\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z\"/></svg><span class=\"like-count\">0</span></button>';var actions=ct.querySelector('.card-actions');if(actions)actions.insertAdjacentElement('afterend',row);else ct.appendChild(row)}var b=row.querySelector('.like-button');b.dataset.likeCode=code;var state=(window.__publicLikes||{})[code]||{count:0,liked:false};setLikeState(d,code,state)}
    function install(d){if(d.getElementById('admin-live-catalog'))return;var style=d.getElementById('admin-catalog-sync');if(!style){style=d.createElement('style');style.id='admin-catalog-sync';style.textContent='del,s{color:#b9b1b5!important;opacity:.58!important}#admin-live-catalog{max-width:1160px;margin:42px auto 56px;padding:0 24px;text-align:center}#admin-live-catalog h2{font:700 30px Georgia,serif;color:#3f5a46;margin:0 0 8px}#admin-live-catalog .admin-catalog-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),250px));justify-content:center;gap:20px;margin-top:20px}.admin-filter-menu button{display:block;width:100%;border:0;background:transparent;text-align:left;cursor:pointer}#admin-live-catalog .card[hidden]{display:none!important}.editorial-section .editorial-grid,.editorial-section .curated-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),280px))!important;justify-content:center!important}.editorial-section .card{width:100%;max-width:280px;min-width:0;justify-self:center}#koleksiyonlar .collection-art-grid{max-width:1000px;margin:24px auto 0;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),280px));justify-content:center;gap:20px}#koleksiyonlar .collection-art-grid .card{width:100%;max-width:280px;min-width:0;justify-self:center}.like-row{display:flex;justify-content:flex-end;margin-top:5px}.like-button{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:44px;padding:5px 8px;border:0;border-radius:999px;background:transparent;color:#927282;font:700 12px/1 Arial,sans-serif;cursor:pointer;transition:color .18s ease,background .18s ease,transform .18s ease}.like-button:hover{background:#fbf0f3;color:#d64f79;transform:translateY(-1px)}.like-button svg{width:19px;height:19px;fill:transparent;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;transition:fill .18s ease,transform .18s ease}.like-button[aria-pressed=true]{color:#df4f7b}.like-button[aria-pressed=true] svg{fill:currentColor;transform:scale(1.06)}.like-button:disabled{opacity:.62;cursor:wait}.like-button:focus-visible{outline:2px solid #b87b96;outline-offset:2px}@media(max-width:600px){#admin-live-catalog{padding:0 14px}}';d.head.appendChild(style)}
    var sold=d.querySelector('#sold-works-grid');if(!sold)return;
    var carouselStyle=d.getElementById('responsive-featured-carousel');if(!carouselStyle){carouselStyle=d.createElement('style');carouselStyle.id='responsive-featured-carousel';carouselStyle.textContent='.fw.is-static .ftt[data-loop-copies="1"]{animation:none!important;transform:none!important;width:100%!important;justify-content:center!important;flex-wrap:wrap!important}@keyframes admin-featured-drift{to{transform:translateX(var(--featured-distance,0px))}}.fw.is-static .prev-default,.fw.is-static .next-default{display:none!important}.fw.is-manual .ftt{animation:none!important;transition:transform .65s ease!important}.all-works-section{max-width:1160px;margin:48px auto 60px;padding:30px 24px;background:#fffdf9;border:1px solid #efe4dd;border-radius:22px;box-shadow:0 12px 35px #5441370b}.all-works-filter{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;margin:0 auto 18px}.all-works-filter label{font-size:13px;color:#665c61}.all-works-filter select{min-width:220px;border:1px solid #e0d6d1;border-radius:999px;padding:10px 16px;background:#fff;color:#4b514e}.category-manager{border:1px solid #e8ddd7;border-radius:14px;padding:16px;margin:6px 0 18px}.category-manager legend,.size-choice legend,.category-checks legend{padding:0 8px;color:#4b514e;font-weight:700}.category-setting-row{display:flex;gap:9px;margin:8px 0}.category-setting-row input{flex:1;min-width:0}.size-choice{display:flex;align-items:end;gap:10px;border:1px solid #e8ddd7;border-radius:12px;padding:14px}.size-choice label{flex:1;display:grid;gap:6px}.size-choice input,.size-choice select{border:1px solid #e0d6d1;background:#fffdfb;border-radius:10px;padding:10px;width:100%}.size-x{padding-bottom:8px}.category-checks{display:flex;gap:16px;flex-wrap:wrap;border:1px solid #e8ddd7;border-radius:12px;padding:14px}.category-checks label{display:inline-flex;gap:7px;align-items:center}.code-input-row input{flex:1;min-width:0}.copy-code{border:0;border-radius:14px;background:#f6edf1;color:#704c67;font-size:11px;padding:5px 8px;cursor:pointer}.copy-code:hover{background:#ead9e2}@media(max-width:650px){.size-choice{flex-wrap:wrap}.all-works-section{margin:28px 12px;padding:20px 12px}}';d.head.appendChild(carouselStyle)}
    var filterMenu=Array.from(d.querySelectorAll('details')).find(function(x){return (x.querySelector('summary')||{}).textContent.trim().startsWith('Kategori')}),oldControls=filterMenu&&filterMenu.parentElement&&filterMenu.parentElement.parentElement;if(oldControls){oldControls.classList.add('admin-filter-menu');var menus=oldControls.querySelectorAll('details');menus.forEach(function(menu,index){var label=index===0?'Kategori':index===1?'Fiyat':'Sırala',summary=menu.querySelector('summary'),list=menu.querySelector('div');if(summary)summary.dataset.menuLabel=label;if(list)list.dataset.menu=label.toLowerCase()})}
    var section=d.createElement('section');section.id='admin-live-catalog';section.className='all-works-section';section.innerHTML='<header class="section-heading"><span class="eyebrow">ATÖLYEDEN TÜM ÇALIŞMALAR</span><h2>Tüm Eserler</h2><p>Atölyedeki eserleri kategoriye göre keşfedin.</p></header><div class="all-works-filter"><label for="all-works-category">Kategori</label><select id="all-works-category"><option value="">Tüm kategoriler</option></select></div><div class="admin-catalog-grid"></div>';var curatedSection=d.querySelector('#sanatcinin-secimi');(curatedSection||sold).insertAdjacentElement('afterend',section);var allFilter=section.querySelector('.all-works-filter');if(oldControls&&allFilter){Array.from(oldControls.querySelectorAll('details')).forEach(function(menu,index){if(index===0){menu.remove();return}allFilter.appendChild(menu)});oldControls.remove();allFilter.classList.add('admin-filter-menu')}
    if(!d.__galleryLikesBound){d.__galleryLikesBound=true;d.addEventListener('click',function(e){var b=e.target.closest('.like-button');if(!b||b.disabled)return;e.preventDefault();var code=b.dataset.likeCode,liked=b.dataset.liked!=='1';b.disabled=true;fetch('/api/likes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,visitor:likeVisitor,liked:liked})}).then(function(r){if(!r.ok)throw Error('like');return r.json()}).then(function(result){setLikeState(d,result.code,result)}).catch(function(){b.disabled=false}).finally(function(){b.disabled=false})},true);fetch('/api/likes?visitor='+encodeURIComponent(likeVisitor),{cache:'no-store'}).then(function(r){if(!r.ok)throw Error('likes');return r.json()}).then(function(data){Object.keys(data.likes||{}).forEach(function(code){setLikeState(d,code,data.likes[code])})}).catch(function(){})}
    d.addEventListener('change',function(e){if(e.target&&e.target.id==='all-works-category'){filter.category=e.target.value;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map())}},true);d.addEventListener('click',function(e){var option=e.target.closest('.admin-filter-menu [data-filter-value]');if(option){e.preventDefault();var menu=option.closest('details'),label=menu&&menu.querySelector('summary');if(!label)return;var type=label.dataset.menuLabel;if(type==='Kategori')filter.category=option.dataset.filterValue;else if(type==='Fiyat')filter.price=option.dataset.filterValue;else filter.sort=option.dataset.filterValue;label.firstChild.nodeValue=option.textContent.trim()+' ';menu.open=false;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map());return}
    var arrow=e.target.closest('[data-featured-step]');if(arrow){e.preventDefault();e.stopImmediatePropagation();var track=d.querySelector('.fw .ftt'),cards=track&&track.querySelectorAll('.card');if(track&&cards&&cards.length){var copies=Math.max(1,Number(track.dataset.loopCopies)||1),count=Math.max(1,Math.floor(cards.length/copies));window.__adminSlide=((window.__adminSlide||0)+(Number(arrow.dataset.featuredStep)>0?1:-1)+count)%count;var root=track.closest('.fw');if(root)root.classList.add('is-manual');track.style.setProperty('animation','none','important');track.style.transition='transform .65s ease';track.style.transform='translateX(-'+(window.__adminSlide*(cards[0].getBoundingClientRect().width+24))+'px)';if(root.__featuredAutoResume)clearTimeout(root.__featuredAutoResume);root.__featuredAutoResume=setTimeout(function(){root.classList.remove('is-manual');track.style.transform='';var vp=track.parentElement;track.style.setProperty('--featured-distance','-'+Math.max(0,track.scrollWidth-(vp?vp.clientWidth:window.innerWidth))+'px');track.style.setProperty('animation','admin-featured-drift 48s ease-in-out infinite alternate','important')},7000)}}var tile=e.target.closest('.collection-tile[data-category]');if(tile){filter.category=tile.dataset.category;renderCatalog(d,window.__adminProducts||[],window.__adminTemplates||new Map());d.querySelector('#admin-live-catalog').scrollIntoView({behavior:'smooth',block:'start'})}},true);
    }
    function cardTemplate(d,p){var all=Array.from(d.querySelectorAll('.card')),found=all.find(function(x){var chip=x.querySelector('.chip');return chip&&chip.textContent.trim()===p.code});return found||all[0]}
    function paint(d,card,p,cfg){card.hidden=false;card.dataset.productCode=p.code;var chip=card.querySelector('.chip');if(chip)chip.textContent=p.code;var title=card.querySelector('.ct .sf');if(title)title.textContent=p.title;var ct=card.querySelector('.ct');if(ct){var size=ct.querySelector('span:not(.pr)');if(size)size.textContent=p.size+(p.category?' · '+p.category:'');var price=ct.querySelector('.pr');if(price){price.replaceChildren();if(p.sale_price&&Number(p.sale_price)<Number(p.price)){var old=d.createElement('del');old.textContent=fmt(p.price);price.appendChild(old);price.appendChild(d.createTextNode(' '))}var current=d.createElement('b');current.textContent=fmt(p.sale_price&&Number(p.sale_price)<Number(p.price)?p.sale_price:p.price);price.appendChild(current)}var desc=ct.querySelector('.catalog-description');if(!desc){desc=d.createElement('span');desc.className='catalog-description';desc.style.cssText='display:block;margin:8px auto 12px;max-width:96%;color:#827783;font-size:11px;line-height:1.45;text-align:center;min-height:1.45em';var actions=ct.querySelector('.card-actions');ct.insertBefore(desc,actions||null)}desc.textContent=p.description||'';var actions=ct.querySelector('.card-actions');if(actions){actions.replaceChildren();if(p.sold){var sold=d.createElement('span');sold.className='btn g sold-tag';sold.textContent='Satıldı';actions.appendChild(sold)}else{var buy=d.createElement('a');buy.className='btn g';buy.href=p.whatsapp_url||cfg.whatsapp_url||'#iletisim';buy.textContent='Satın Al';if(buy.href.indexOf('http')===0){buy.target='_blank';buy.rel='noopener'}actions.appendChild(buy)}var inspect=d.createElement('button');inspect.type='button';inspect.className='btn inspect-btn';inspect.textContent='İncele';actions.appendChild(inspect)}}var art=card.querySelector('.art');if(art){if(p.image){var img=art.querySelector('img');if(!img){art.replaceChildren();img=d.createElement('img');img.style.cssText='position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:inherit';art.appendChild(img)}img.src='/'+p.image;img.alt=p.title}else if(art.querySelector('img')){art.querySelector('img').remove()}}ensureLikeRow(d,card,p.code)}
    function fmt(n){return '₺'+Number(n||0).toLocaleString('tr-TR')}
    function renderCatalog(d,products,templates){var active=products.filter(function(p){return !p.archived&&p.published!==false}),grid=d.querySelector('#admin-live-catalog .admin-catalog-grid');if(!grid)return;var rows=active.filter(function(p){if(filter.category&&p.category!==filter.category)return false;var amount=Number(p.sale_price&&Number(p.sale_price)<Number(p.price)?p.sale_price:p.price);if(filter.price==='under')return amount<3000;if(filter.price==='middle')return amount>=3000&&amount<4000;if(filter.price==='high')return amount>=4000;return true});rows.sort(function(a,b){if(filter.sort==='low')return Number(a.sale_price||a.price)-Number(b.sale_price||b.price);if(filter.sort==='high')return Number(b.sale_price||b.price)-Number(a.sale_price||a.price);if(filter.sort==='name')return a.title.localeCompare(b.title,'tr');return b.id-a.id});var base=templates.values().next().value||d.querySelector('.card');if(base)grid.replaceChildren.apply(grid,rows.map(function(p){var clone=(templates.get(p.code)||base).cloneNode(true);paint(d,clone,p,window.__adminSettings||{});return clone}))}
    function sync(){try{var d=frame.contentDocument;if(!d||busy)return;install(d);busy=true;fetch('/api/products',{cache:'no-store'}).then(function(r){if(!r.ok)throw Error('catalog');return r.json()}).then(function(data){var products=data.products||[],cfg=data.settings||{},active=products.filter(function(p){return !p.archived&&!p.sold&&p.published!==false}),featured=Array.from(new Map(active.filter(function(p){return !!p.featured}).map(function(p){return[p.code,p]})).values()).sort(function(a,b){return b.id-a.id}),soldItems=products.filter(function(p){return !p.archived&&!!p.sold&&p.published!==false}).sort(function(a,b){return b.id-a.id}),templates=new Map();Array.from(d.querySelectorAll('.card')).forEach(function(c){var chip=c.querySelector('.chip');if(chip&&!templates.has(chip.textContent.trim()))templates.set(chip.textContent.trim(),c)});window.__adminProducts=products;window.__adminTemplates=templates;window.__adminSettings=cfg;
    var ft=d.querySelector('.fw .ftt'),fallback=d.querySelector('.card');if(ft&&fallback){var viewport=ft.parentElement,cardWidth=(templates.get(featured[0]&&featured[0].code)||fallback).getBoundingClientRect().width||260,gap=24,needsLoop=featured.length>0&&featured.length*(cardWidth+gap)-gap>(viewport?viewport.clientWidth:window.innerWidth),cycle=featured.slice();var featuredSignature=featured.map(function(p){return p.code}).join('|')+'|'+(needsLoop?'loop':'static');ft.dataset.loopCopies='1';var featuredRoot=ft.closest('.fw');if(featuredRoot)featuredRoot.classList.toggle('is-static',!needsLoop);if(ft.dataset.featuredSignature!==featuredSignature){ft.dataset.featuredSignature=featuredSignature;ft.replaceChildren.apply(ft,cycle.map(function(p){var card=(templates.get(p.code)||fallback).cloneNode(true);paint(d,card,p,cfg);return card}));ft.style.setProperty('--featured-distance','-'+Math.max(0,ft.scrollWidth-(viewport?viewport.clientWidth:window.innerWidth))+'px');ft.style.setProperty('animation',needsLoop?'admin-featured-drift 48s ease-in-out infinite alternate':'none','important');ft.style.transform='';if(!featured.length)ft.innerHTML='<p style="padding:24px;color:#827783">Yönetim panelinden öne çıkarılan eserler burada görünür.</p>'}
    var arrivals=d.querySelector('#yeni-gelenler .editorial-grid');if(arrivals){var fresh=active.filter(function(p){return !!p.show_new}).sort(function(a,b){return b.id-a.id});arrivals.replaceChildren.apply(arrivals,fresh.map(function(p){var c=(templates.get(p.code)||fallback).cloneNode(true);paint(d,c,p,cfg);return c}));arrivals.parentElement.hidden=!fresh.length}
    var collectionTiles=d.querySelector('#koleksiyonlar .collection-grid'),collectionGrid=d.querySelector('#koleksiyonlar .collection-art-grid');if(collectionTiles&&!collectionGrid){collectionGrid=d.createElement('div');collectionGrid.className='editorial-grid collection-art-grid';collectionGrid.setAttribute('aria-label','Koleksiyon eserleri');collectionTiles.insertAdjacentElement('afterend',collectionGrid)}var collectionWorks=active.filter(function(p){return !!p.show_collections}).sort(function(a,b){return b.id-a.id});if(collectionGrid){collectionGrid.replaceChildren.apply(collectionGrid,collectionWorks.map(function(p){var c=(templates.get(p.code)||fallback).cloneNode(true);paint(d,c,p,cfg);return c}));collectionGrid.hidden=!collectionWorks.length}
    var curated=d.querySelector('#sanatcinin-secimi .curated-grid');if(curated){var picks=active.filter(function(p){return !!p.show_curated}).sort(function(a,b){return b.id-a.id});curated.replaceChildren.apply(curated,picks.map(function(p){var c=(templates.get(p.code)||fallback).cloneNode(true);paint(d,c,p,cfg);return c}));curated.parentElement.hidden=!picks.length}
    var soldGrid=d.querySelector('#sold-works-grid');if(soldGrid){soldGrid.classList.add('sold-works-grid');soldGrid.replaceChildren.apply(soldGrid,soldItems.map(function(p){var c=(templates.get(p.code)||fallback).cloneNode(true);paint(d,c,p,cfg);return c}));soldGrid.parentElement.hidden=!soldItems.length}
    var cats=Array.from(new Set((cfg.categories||'').split(',').map(function(x){return x.trim()}).filter(Boolean).concat(products.map(function(p){return(p.category||'').trim()}).filter(Boolean))));var allCategory=d.querySelector('#all-works-category');if(allCategory){var previous=filter.category;allCategory.replaceChildren.apply(allCategory,[new Option('Tüm kategoriler','')].concat(cats.map(function(x){return new Option(x,x)})));allCategory.value=cats.indexOf(previous)>=0?previous:'';filter.category=allCategory.value}var categoryMenu=Array.from(d.querySelectorAll('.admin-filter-menu details')).find(function(x){return x.querySelector('summary')&&x.querySelector('summary').dataset.menuLabel==='Kategori'});if(categoryMenu){var list=categoryMenu.querySelector('[data-menu]');list.replaceChildren();[['','Tümü']].concat(cats.map(function(x){return[x,x]})).forEach(function(entry){var b=d.createElement('button');b.type='button';b.dataset.filterValue=entry[0];b.textContent=entry[1];list.appendChild(b)})}Array.from(d.querySelectorAll('#koleksiyonlar .collection-tile')).forEach(function(tile,i){var category=cats[i];if(!category){tile.hidden=true;return}tile.hidden=false;tile.dataset.category=category;tile.href='#admin-live-catalog';var label=tile.querySelector('span'),heading=tile.querySelector('h3'),copy=tile.querySelector('p');if(label)label.textContent=('0'+(i+1)).slice(-2)+' · '+category.toLocaleUpperCase('tr');if(heading)heading.textContent=category;if(copy)copy.textContent='Bu kategorideki '+active.filter(function(p){return p.category===category}).length+' eseri koleksiyonda görüntüleyin.'});
    var menus=Array.from(d.querySelectorAll('.admin-filter-menu details'));menus.forEach(function(menu){var s=menu.querySelector('summary'),list=menu.querySelector('[data-menu]');if(!s||!list||s.dataset.menuLabel==='Kategori')return;var opts=s.dataset.menuLabel==='Fiyat'?[['','Tüm fiyatlar'],['under','₺3.000 altı'],['middle','₺3.000–₺4.000'],['high','₺4.000 üzeri']]:[['new','En yeni'],['low','Fiyat: düşükten yükseğe'],['high','Fiyat: yüksekten düşüğe'],['name','Ada göre']];list.replaceChildren.apply(list,opts.map(function(entry){var b=d.createElement('button');b.type='button';b.dataset.filterValue=entry[0];b.textContent=entry[1];return b}))});
    var brand=d.querySelector('.brand small');if(brand)brand.textContent='EL YAPIMI TABLOLAR · '+(cfg.site_name||'Perihan Baktaş');var name=d.querySelector('#hakkimda .sc[style*="font-size:40px"]');if(name)name.textContent=cfg.site_name||'Perihan Baktaş';d.title=(cfg.site_name||'Perihan Baktaş')+' | Sanat Atölyesi';[['Instagram','instagram_url'],['TikTok','tiktok_url'],['Telegram','telegram_url'],['WhatsApp','whatsapp_url']].forEach(function(pair){var url=cfg[pair[1]];if(!url)return;Array.from(d.querySelectorAll('a')).filter(function(a){return a.textContent.trim()===pair[0]}).forEach(function(a){a.href=url;a.target='_blank';a.rel='noopener'})});renderCatalog(d,products,templates);
    var sig=JSON.stringify([products.map(function(p){return[p.id,p.code,p.title,p.size,p.price,p.sale_price,p.category,p.description,p.image,p.whatsapp_url,p.featured,p.sold,p.archived,p.show_new,p.show_collections,p.show_curated]}),cfg]);if(sig!==lastSignature){lastSignature=sig;window.__adminSlide=0;if(ft){ft.style.transform='';ft.style.animation='';}}}}).catch(function(){}).finally(function(){busy=false})}catch(e){busy=false}}
    frame.addEventListener('load',function(){sync();setInterval(sync,2500);try{frame.contentWindow.addEventListener('resize',function(){lastSignature='';sync()})}catch(e){}});if(frame.contentDocument&&frame.contentDocument.readyState==='complete'){sync();setInterval(sync,2500)}})();
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

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
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
        self.redirect("/atolye-yonetim-8f31/login")
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
                for item in items:
                    item["published"] = not item.get("publish_at") or item["publish_at"] <= datetime.now().strftime("%Y-%m-%dT%H:%M")
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
        if path == "/api/likes":
            visitor = query.get("visitor", [""])[0]
            if not re.fullmatch(r"[a-f0-9-]{16,64}", visitor):
                visitor = ""
            with connect() as c:
                rows = c.execute("""
                    SELECT p.code, COUNT(l.visitor_id) AS count,
                    MAX(CASE WHEN l.visitor_id=? THEN 1 ELSE 0 END) AS liked
                    FROM products p LEFT JOIN product_likes l ON l.product_id=p.id
                    WHERE p.archived=0 GROUP BY p.id ORDER BY p.id
                """, (visitor,)).fetchall()
            return self.send_json({"likes": {r["code"]: {"count": r["count"], "liked": bool(r["liked"])} for r in rows}})
        if path.startswith("/static/"):
            return self.static(path)
        if path.startswith("/uploads/"):
            relative = path.removeprefix("/")
            if relative.startswith("uploads/requests/") and not self.get_admin():
                return self.send_error(404)
            file = (DATA_ROOT / relative).resolve()
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
                sql = "SELECT * FROM products WHERE archived=0 AND sold=0 AND (publish_at='' OR publish_at<=?)"
                args = [datetime.now().strftime("%Y-%m-%dT%H:%M")]
                if category:
                    sql += " AND category=?"; args.append(category)
                order = "created_at DESC"
                if sort == "fiyat-artan": order = "COALESCE(sale_price,price) ASC"
                elif sort == "fiyat-azalan": order = "COALESCE(sale_price,price) DESC"
                rows = c.execute(sql + " ORDER BY featured DESC," + order, args).fetchall()
                featured = c.execute("SELECT * FROM products WHERE archived=0 AND sold=0 AND featured=1 AND (publish_at='' OR publish_at<=?) ORDER BY id DESC LIMIT 8", (datetime.now().strftime("%Y-%m-%dT%H:%M"),)).fetchall()
                sold = c.execute("SELECT * FROM products WHERE archived=0 AND sold=1 AND (publish_at='' OR publish_at<=?) ORDER BY id DESC", (datetime.now().strftime("%Y-%m-%dT%H:%M"),)).fetchall()
            cats = [x.strip() for x in settings().get("categories", "").split(",") if x.strip()]
            select = "".join(f"<option {'selected' if category == x else ''} value='{esc(x)}'>{esc(x)}</option>" for x in cats)
            hero = "<section class='hero'><div class='hero-copy'><span class='eyebrow'>EL YAPIMI · ÖZGÜN ESERLER</span><h1>Sanatla Dolu<br><em>Huzurlu Bir Bahar</em></h1><p>İlkbaharın sakinliği, fırçanın dokunuşuyla duvarınıza gelsin. Her eser kendine özgü bir renk ve hikâye taşır.</p><a class='button' href='#eserler'>Eserleri Keşfet</a></div><div class='hero-art'><div class='hero-canvas'><span>✿</span><span>✿</span><span>✿</span><span>✿</span></div><small>Perihan Baktaş · Atölyeden</small></div></section>"
            content = hero
            if featured:
                content += f"<section class='section'><div class='section-heading'><span class='eyebrow'>ATÖLYEDEN SEÇKİ</span><h2>Öne Çıkan Eserler</h2><p>Sanatın en özel parçalarını keşfedin.</p></div><div class='carousel'><button class='carousel-arrow' type='button' data-carousel='prev' aria-label='Önceki eserler'>‹</button><div class='product-grid carousel-track'>{product_cards(featured)}</div><button class='carousel-arrow' type='button' data-carousel='next' aria-label='Sonraki eserler'>›</button></div></section>"
            content += f"<section class='section' id='eserler'><div class='section-heading'><span class='eyebrow'>ÖZGÜN ÇALIŞMALAR</span><h2>Eser Koleksiyonu</h2><p>Size yakın renkleri ve manzaraları seçin.</p></div><form class='filters' method='get'><label>Kategori<select name='kategori'><option value=''>Tüm kategoriler</option>{select}</select></label><label>Sırala<select name='sirala'><option value=''>Öne çıkanlar</option><option value='fiyat-artan' {'selected' if sort=='fiyat-artan' else ''}>Fiyat: düşükten yükseğe</option><option value='fiyat-azalan' {'selected' if sort=='fiyat-azalan' else ''}>Fiyat: yüksekten düşüğe</option></select></label><button class='button small'>Uygula</button></form><div class='product-grid'>{product_cards(rows)}</div></section>"
            if sold:
                content += f"<section class='section sold-section'><div class='section-heading'><span class='eyebrow'>YENİ SAHİPLERİNE ULAŞTILAR</span><h2>Satılan Eserler</h2><p>Sahiplerine ulaşmış güzel parçalar.</p></div><div class='product-grid'>{product_cards(sold)}</div></section>"
            content += "<section id='hakkimda' class='about'><span class='eyebrow'>ATÖLYEDEN BİR NOT</span><h2>Her Eserde Bir Bahar Hikâyesi</h2><p>Perihan Baktaş’ın el yapımı eserleri; çiçeklerin, doğanın ve mevsimlerin renklerinden ilham alır.</p></section>"
            return self.send_html(render("Ana Sayfa", content))
        if path == "/arsiv":
            with connect() as c: rows = c.execute("SELECT * FROM products WHERE archived=1 ORDER BY created_at DESC").fetchall()
            content = f"<section class='page-intro'><span class='eyebrow'>ATÖLYE KAYITLARI</span><h1>Eser Arşivi</h1><p>Arşive alınan eserler bu listede saklanır.</p></section><div class='product-grid'>{product_cards(rows)}</div>"
            return self.send_html(render("Eser Arşivi", content))
        if path in ("/atolye-yonetim-8f31", "/atolye-yonetim-8f31/"):
            return self.redirect("/atolye-yonetim-8f31/products" if self.get_admin() else "/atolye-yonetim-8f31/login")
        if path == "/atolye-yonetim-8f31/setup":
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            if exists: return self.redirect("/atolye-yonetim-8f31/login")
            content = "<section class='page-intro'><span class='eyebrow'>İLK KURULUM</span><h1>Yönetici Parolası Oluştur</h1><p>Bu panel yalnızca sizin belirleyeceğiniz parola ile açılır. En az 10 karakter kullanın.</p></section><section class='narrow form-card'><form method='post' action='/atolye-yonetim-8f31/setup'><label>Yeni parola<input type='password' name='password' minlength='10' required></label><label>Parolayı doğrula<input type='password' name='confirm' minlength='10' required></label><button class='button wide'>Yönetici Hesabı Oluştur</button></form></section>"
            return self.send_html(render("İlk Kurulum", content))
        if path == "/atolye-yonetim-8f31/login":
            content = "<section class='page-intro'><span class='eyebrow'>YÖNETİM PANELİ</span><h1>Yönetici Girişi</h1><p>Atölye yönetimine devam etmek için giriş yapın.</p></section><section class='narrow form-card'><form method='post' action='/atolye-yonetim-8f31/login'><label>Parola<input type='password' name='password' required autofocus></label><button class='button wide'>Giriş Yap</button></form></section>"
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            return self.send_html(render("Yönetici Girişi", content + ("" if exists else "<p class='center'><a href='/atolye-yonetim-8f31/setup'>İlk yönetici parolasını oluştur</a></p>")))
        if not path.startswith("/atolye-yonetim-8f31/"):
            return self.send_error(404)
        admin = self.require_admin()
        if not admin: return
        csrf = esc(admin["csrf"])
        if path == "/atolye-yonetim-8f31/logout":
            return self.redirect("/atolye-yonetim-8f31/login", [("Set-Cookie", "gallery_admin=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")])
        if path == "/atolye-yonetim-8f31/products":
            with connect() as c: rows = c.execute("SELECT * FROM products WHERE archived=0 ORDER BY featured DESC,id").fetchall()
            listing_rows = []
            with connect() as c:
                for p in rows:
                    likes = c.execute("SELECT COUNT(*) FROM product_likes WHERE product_id=?", (p["id"],)).fetchone()[0]
                    code_cell = f"<code>{esc(p['code'])}</code> <button type='button' class='copy-code' data-copy='{esc(p['code'])}' title='Eser kodunu kopyala' aria-label='Eser kodunu kopyala'>Kopyala</button>"
                    state = "Taslak" if p["publish_at"] and p["publish_at"] > date.today().isoformat() else ("Satıldı" if p["sold"] else "Yayında")
                    sold_button = "Satışa Aç" if p["sold"] else "Satıldı Olarak İşaretle"
                    listing_rows.append(f"<tr><td>{code_cell}</td><td>{esc(p['title'])}</td><td>{esc(p['size'])}</td><td>{esc(p['category'])}</td><td>{money(p['sale_price'] or p['price'])}</td><td>{likes} ♥</td><td>{esc(product_sections(p))}</td><td>{esc(state)}{(' · '+esc(p['publish_at'])) if p['publish_at'] else ''}</td><td><a href='/atolye-yonetim-8f31/products/{p['id']}'>Düzenle</a> · <form class='inline-form' method='post' action='/atolye-yonetim-8f31/products/{p['id']}/sold'><input type='hidden' name='csrf' value='{csrf}'><button class='text-button'>{sold_button}</button></form> · <form class='inline-form' method='post' action='/atolye-yonetim-8f31/products/{p['id']}/archive'><input type='hidden' name='csrf' value='{csrf}'><button class='text-button'>Arşivle</button></form></td></tr>")
            listing = "".join(listing_rows)
            copy_script = "<script>document.querySelectorAll('.copy-code').forEach(function(b){b.addEventListener('click',function(){navigator.clipboard.writeText(b.dataset.copy).then(function(){var old=b.textContent;b.textContent='Kopyalandı';setTimeout(function(){b.textContent=old},1200)})})})</script>"
            content = f"<section class='admin-top'><div><span class='eyebrow'>KATALOG</span><h1>Tablolar</h1><p>Fiyat, ölçü, kategori, açıklama ve öne çıkarma ayarları.</p></div>{admin_nav('products')}</section><p><a class='button small' href='/atolye-yonetim-8f31/products/new'>+ Yeni Tablo Ekle</a></p><div class='table-wrap'><table><thead><tr><th>Kod</th><th>Eser</th><th>Ölçü</th><th>Kategori</th><th>Fiyat</th><th>Beğeni</th><th>Ana sayfa bölümleri</th><th>Durum / yayın tarihi</th><th>İşlem</th></tr></thead><tbody>{listing}</tbody></table></div><h2>Arşiv</h2><p><a href='/arsiv'>Arşivdeki eserleri görüntüle</a></p>{copy_script}"
            return self.send_html(render("Yönetim · Tablolar", content))
        if path == "/atolye-yonetim-8f31/products/new" or re.fullmatch(r"/atolye-yonetim-8f31/products/\d+", path):
            product = None
            if path != "/atolye-yonetim-8f31/products/new":
                with connect() as c: product = c.execute("SELECT * FROM products WHERE id=?", (int(path.rsplit('/',1)[-1]),)).fetchone()
                if not product: return self.send_error(404)
            val = lambda key, default="": product[key] if product else default
            size_match = re.match(r"\s*(\d+)\s*[x×]\s*(\d+)\s*(.*)", str(val("size", "")), re.I)
            width_val, height_val, unit_val = (size_match.group(1), size_match.group(2), size_match.group(3).strip() or "cm") if size_match else ("", "", "cm")
            cats = [x.strip() for x in settings().get("categories", "").split(",") if x.strip()]
            if product and product["category"] and product["category"] not in cats: cats.append(product["category"])
            if not product:
                with connect() as c:
                    while True:
                        code = "PB-" + str(secrets.randbelow(900) + 100)
                        if not c.execute("SELECT 1 FROM products WHERE code=?", (code,)).fetchone(): break
            else:
                code = product["code"]
            code_field = f"<label>Eser kodu<div class='code-input-row'><input name='code' value='{esc(code)}' required><button type='button' class='copy-code' data-copy='{esc(code)}'>Kopyala</button></div></label>"
            category_checks = "".join(f"<label><input type='checkbox' name='category_choice' value='{esc(x)}' {'checked' if product and product['category']==x else ''}>{esc(x)}</label>" for x in cats)
            featured = "checked" if product and product["featured"] else ""
            sold = "checked" if product and product["sold"] else ""
            show_new = "checked" if product and product["show_new"] else ""
            show_collections = "checked" if product and product["show_collections"] else ""
            show_curated = "checked" if product and product["show_curated"] else ""
            section_choices = f"<fieldset class='section-choice span-2'><legend>Ana sayfada hangi bölümlerde görünsün?</legend><p>En az bir bölüm seçin; aynı tabloyu birden fazla bölümde gösterebilirsiniz.</p><div class='section-checks'><label><input type='checkbox' name='show_new' value='1' {show_new}> Yeni Gelenler</label><label><input type='checkbox' name='show_collections' value='1' {show_collections}> Koleksiyonlar</label><label><input type='checkbox' name='show_curated' value='1' {show_curated}> Sanatçının Seçkisi</label></div></fieldset>"
            size_fields = f"<fieldset class='span-2 size-choice'><legend>Tablo ölçüsü</legend><label>Genişlik<input type='number' name='width' min='1' max='500' value='{esc(width_val)}' required></label><span class='size-x'>×</span><label>Yükseklik<input type='number' name='height' min='1' max='500' value='{esc(height_val)}' required></label><label>Birim<select name='size_unit'><option {'selected' if unit_val=='cm' else ''}>cm</option><option {'selected' if unit_val=='mm' else ''}>mm</option><option {'selected' if unit_val=='inç' else ''}>inç</option></select></label></fieldset>"
            category_choices = f"<fieldset class='span-2 category-checks'><legend>Kategori seçin</legend>{category_checks or '<small>Önce Ayarlar bölümünden kategori ekleyin.</small>'}</fieldset>"
            publish_at = val("publish_at", "")
            if publish_at and len(publish_at) == 10: publish_at += "T00:00"
            content = f"<section class='admin-top'><div><span class='eyebrow'>KATALOG</span><h1>{'Tabloyu Düzenle' if product else 'Yeni Tablo Ekle'}</h1></div>{admin_nav('products')}</section><section class='form-card admin-form'><form method='post' enctype='multipart/form-data' action='/atolye-yonetim-8f31/products/save'><input type='hidden' name='csrf' value='{csrf}'><input type='hidden' name='id' value='{esc(val('id'))}'><div class='form-grid'>{code_field}{input_field('Eser adı', 'title', val('title'), required=True)}{size_fields}{category_choices}{input_field('Liste fiyatı (₺)', 'price', val('price'), 'number', True, "min='0'")}{input_field('İndirimli fiyat (₺, isteğe bağlı)', 'sale_price', val('sale_price') or '', 'number', False, "min='0'")}{input_field('Yayın zamanı (boş bırakılırsa hemen yayınlanır)', 'publish_at', publish_at, 'datetime-local')}{input_field('WhatsApp bağlantısı (isteğe bağlı)', 'whatsapp_url', val('whatsapp_url'), 'url', False, "placeholder='https://wa.me/...' class='span-2'")}{input_field('Açıklama', 'description', val('description'), 'textarea', False, "rows='4' class='span-2'")}<label class='span-2'>Eser görseli<input type='file' name='image' accept='.jpg,.jpeg,.jfif,.png,.webp'><small>JPG, PNG veya WEBP · en fazla 8 MB{(' · Mevcut görsel: '+esc(val('image'))) if product and val('image') else ''}</small></label></div><div class='check-row'><label><input type='checkbox' name='featured' value='1' {featured}> Öne Çıkan Eserler şeridinde göster</label><label><input type='checkbox' name='sold' value='1' {sold}> Satıldı olarak göster</label></div>{section_choices}<button class='button'>Kaydet</button> <a class='button ghost' href='/atolye-yonetim-8f31/products'>İptal</a></form></section><script>document.querySelectorAll('.copy-code').forEach(b=>b.addEventListener('click',()=>navigator.clipboard.writeText(b.dataset.copy)));document.querySelectorAll('.category-checks input').forEach(x=>x.addEventListener('change',()=>{{if(x.checked)document.querySelectorAll('.category-checks input').forEach(y=>{{if(y!==x)y.checked=false}})}}));</script>"
            return self.send_html(render("Yönetim · Tablo", content))
        if path == "/atolye-yonetim-8f31/settings":
            cfg = settings()
            category_rows = "".join(f"<div class='category-setting-row'><input class='category-setting-input' value='{esc(x)}' maxlength='80' aria-label='Kategori adı'><button type='button' class='button ghost category-remove'>Sil</button></div>" for x in cfg.get("categories", "").split(",") if x.strip())
            content = f"<section class='admin-top'><div><span class='eyebrow'>SİTE AYARLARI</span><h1>Bağlantılar ve Kategoriler</h1><p>WhatsApp ve sosyal medya bağlantılarını, kategori listesini yönetin.</p></div>{admin_nav('settings')}</section><section class='narrow form-card'><form id='settings-form' method='post' action='/atolye-yonetim-8f31/settings'><input type='hidden' name='csrf' value='{csrf}'>{input_field('Atölye adı', 'site_name', cfg.get('site_name'), required=True)}{input_field('WhatsApp bağlantısı', 'whatsapp_url', cfg.get('whatsapp_url'), 'url', False, "placeholder='https://wa.me/905...' ")}{input_field('Instagram URL', 'instagram_url', cfg.get('instagram_url'), 'url')}{input_field('TikTok URL', 'tiktok_url', cfg.get('tiktok_url'), 'url')}{input_field('Telegram URL', 'telegram_url', cfg.get('telegram_url'), 'url')}<fieldset class='category-manager'><legend>Kategoriler</legend><div id='category-setting-list'>{category_rows}</div><button type='button' class='button ghost' id='category-add'>+ Kategori Ekle</button><input type='hidden' name='categories' id='categories-value'></fieldset><button class='button wide'>Ayarları Kaydet</button></form></section><script src='/static/category-manager.js' defer></script>"
            return self.send_html(render("Yönetim · Ayarlar", content))
        return self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/likes":
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2048:
                return self.send_json({"error": "İstek çok büyük."}, 413)
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                code = str(data.get("code", "")).strip()[:64]
                visitor = str(data.get("visitor", ""))
                liked = data.get("liked")
                if not code or not re.fullmatch(r"[a-f0-9-]{16,64}", visitor) or not isinstance(liked, bool):
                    return self.send_json({"error": "Beğeni bilgisi geçersiz."}, 400)
                with connect() as c:
                    product = c.execute("SELECT id FROM products WHERE code=? AND archived=0", (code,)).fetchone()
                    if not product:
                        return self.send_json({"error": "Eser bulunamadı."}, 404)
                    if liked:
                        c.execute("INSERT OR IGNORE INTO product_likes(product_id,visitor_id) VALUES(?,?)", (product["id"], visitor))
                    else:
                        c.execute("DELETE FROM product_likes WHERE product_id=? AND visitor_id=?", (product["id"], visitor))
                    count = c.execute("SELECT COUNT(*) FROM product_likes WHERE product_id=?", (product["id"],)).fetchone()[0]
                return self.send_json({"code": code, "count": count, "liked": liked})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                return self.send_json({"error": "İstek okunamadı."}, 400)
        try:
            fields, files = self.parse_form()
        except ValueError as e:
            return self.send_html(render("İstek Hatası", f"<section class='narrow form-card'><h1>İşlem tamamlanamadı</h1><p>{esc(e)}</p><a href='/'>Ana sayfaya dön</a></section>"), 400)
        if path == "/atolye-yonetim-8f31/setup":
            with connect() as c: exists = c.execute("SELECT 1 FROM admin WHERE id=1").fetchone()
            pw = fields.get("password", "")
            if exists: return self.redirect("/atolye-yonetim-8f31/login")
            if len(pw) < 10 or pw != fields.get("confirm"):
                return self.send_html(render("İlk Kurulum", "<section class='narrow form-card'><h1>Parolalar eşleşmiyor</h1><p>En az 10 karakterli, aynı parolayı tekrar girin.</p><a href='/atolye-yonetim-8f31/setup'>Geri dön</a></section>"), 400)
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 310000)
            stored = base64.b64encode(salt + digest).decode()
            with connect() as c: c.execute("INSERT INTO admin(id,password_hash) VALUES(1,?)", (stored,))
            return self.redirect("/atolye-yonetim-8f31/login")
        if path == "/atolye-yonetim-8f31/login":
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
                        return self.redirect("/atolye-yonetim-8f31/products", [("Set-Cookie", f"gallery_admin={payload}.{sig}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800")])
                except Exception: pass
            return self.send_html(render("Giriş Hatası", "<section class='narrow form-card'><h1>Parola hatalı</h1><p>Yönetici parolasını kontrol edip yeniden deneyin.</p><a href='/atolye-yonetim-8f31/login'>Geri dön</a></section>"), 401)
        if path.startswith("/atolye-yonetim-8f31/"):
            admin = self.get_admin()
            if not admin: return self.redirect("/atolye-yonetim-8f31/login")
            if not self.csrf_ok(fields): return self.send_error(403, "İstek doğrulanamadı. Sayfayı yenileyip tekrar deneyin.")
        if path == "/atolye-yonetim-8f31/products/save":
            try:
                pid = int(fields.get("id") or 0)
                code = fields.get("code", "").strip().upper()[:30]
                title = fields.get("title", "").strip()[:120]
                width = int(fields.get("width", "0"))
                height = int(fields.get("height", "0"))
                unit = fields.get("size_unit", "cm").strip()[:8]
                size = f"{width}x{height} {unit}" if width > 0 and height > 0 else ""
                category = fields.get("category_choice", "").strip()[:80]
                publish_at = fields.get("publish_at", "").strip()
                if publish_at:
                    try: publish_at = datetime.fromisoformat(publish_at).strftime("%Y-%m-%dT%H:%M")
                    except ValueError: raise ValueError("Yayın tarihi ve saati geçerli değil.")
                price = int(fields.get("price", "0"))
                sale = int(fields.get("sale_price")) if fields.get("sale_price", "").strip() else None
                desc = fields.get("description", "").strip()[:1500]
                wa = safe_url(fields.get("whatsapp_url", ""))
                if not code or not title or not size or not category or price < 0: raise ValueError("Kod, ad, ölçü, kategori ve geçerli bir fiyat girin.")
                image = self.upload_file(files.get("image"), "works", "work-")
                featured, sold = int(fields.get("featured") == "1"), int(fields.get("sold") == "1")
                show_new = int(fields.get("show_new") == "1")
                show_collections = int(fields.get("show_collections") == "1")
                show_curated = int(fields.get("show_curated") == "1")
                if not (show_new or show_collections or show_curated): raise ValueError("Tablonun görüneceği en az bir ana sayfa bölümü seçin.")
                with connect() as c:
                    if pid:
                        old = c.execute("SELECT image FROM products WHERE id=?", (pid,)).fetchone()
                        if not old: return self.send_error(404)
                        image = image or old["image"]
                        c.execute("UPDATE products SET code=?,title=?,size=?,price=?,sale_price=?,category=?,description=?,image=?,whatsapp_url=?,featured=?,sold=?,show_new=?,show_collections=?,show_curated=?,publish_at=? WHERE id=?", (code,title,size,price,sale,category,desc,image,wa,featured,sold,show_new,show_collections,show_curated,publish_at,pid))
                    else:
                        c.execute("INSERT INTO products(code,title,size,price,sale_price,category,description,image,whatsapp_url,featured,sold,show_new,show_collections,show_curated,publish_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (code,title,size,price,sale,category,desc,image,wa,featured,sold,show_new,show_collections,show_curated,publish_at))
                return self.redirect("/atolye-yonetim-8f31/products")
            except (ValueError, sqlite3.IntegrityError) as e:
                return self.send_html(render("Tablo Kaydedilemedi", f"<section class='narrow form-card'><h1>Tablo kaydedilemedi</h1><p>{esc(e) or 'Eser kodu başka bir tabloda kullanılıyor.'}</p><a href='/atolye-yonetim-8f31/products'>Tablolara dön</a></section>"), 400)
        archive = re.fullmatch(r"/atolye-yonetim-8f31/products/(\d+)/archive", path)
        if archive:
            with connect() as c: c.execute("UPDATE products SET archived=1 WHERE id=?", (int(archive.group(1)),))
            return self.redirect("/atolye-yonetim-8f31/products")
        mark_sold = re.fullmatch(r"/atolye-yonetim-8f31/products/(\d+)/sold", path)
        if mark_sold:
            with connect() as c: c.execute("UPDATE products SET sold=CASE sold WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (int(mark_sold.group(1)),))
            return self.redirect("/atolye-yonetim-8f31/products")
        if path == "/atolye-yonetim-8f31/settings":
            allowed = ("site_name", "whatsapp_url", "instagram_url", "tiktok_url", "telegram_url")
            with connect() as c:
                for key in allowed:
                    val = fields.get(key, "").strip()
                    if key.endswith("_url"): val = safe_url(val)
                    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key,val[:500]))
                categories = ", ".join(dict.fromkeys(x.strip()[:80] for x in fields.get("categories", "").split(",") if x.strip()))
                c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('categories',?)", (categories,))
            return self.redirect("/atolye-yonetim-8f31/settings")
        return self.send_error(404)


def admin_nav(active):
    links = (("products", "Tablolar", "/atolye-yonetim-8f31/products"), ("settings", "Site Ayarları", "/atolye-yonetim-8f31/settings"))
    return "<nav class='admin-nav'>" + "".join(f"<a class='{'active' if key==active else ''}' href='{url}'>{label}</a>" for key,label,url in links) + "<a href='/atolye-yonetim-8f31/logout'>Çıkış</a></nav>"


if __name__ == "__main__":
    init_db()
    host = os.environ.get("GALLERY_HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("GALLERY_PORT", "8000")))
    print(f"Sanat Atölyesi is running at http://{host}:{port}")
    print("First visit: /atolye-yonetim-8f31/setup to create the administrator password.")
    ThreadingHTTPServer((host, port), SiteHandler).serve_forever()


