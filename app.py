"""
Moon Cafe Interlaken - zweisprachige Webanwendung fuer die VICC-Praxisarbeit.

Kunde: das Moon Cafe in Interlaken, ein beliebtes Cafe.
Die Anwendung wird in Azure App Service bereitgestellt.

Funktionen:
- Startseite: Vorstellung, Live-Anzeige "jetzt geoeffnet?", volles Menue, Zeiten
- Tischreservierung mit Pruefung:
    Vorname/Nachname, E-Mail und Telefon (Formatpruefung),
    Datum (Donnerstag gesperrt, Vergangenheit gesperrt),
    Zeit (15-Minuten-Slots innerhalb der Oeffnungszeiten, belegte Zeiten
    nicht waehlbar), Personen, Kinderhochstuhl, Sitzplatz
- Sprachwahl Deutsch / Englisch (?lang=de / ?lang=en)
- Web-API (JSON): /api/status, /api/menu, /api/oeffnung

Design: ruhige, moderne Aesthetik, responsiv (Handy-tauglich). Zustandslos,
keine Datenbank; persistente Speicherung der Reservierungen ist als
Ausbaumoeglichkeit (DBaaS) vorgesehen.
"""

import os
import re
from datetime import datetime, date, time, timezone
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
app.json.compact = False          # JSON lesbar einruecken
app.json.ensure_ascii = False     # Umlaute korrekt ausgeben (z. B. Café)

# ---------------------------------------------------------------------------
# Stammdaten (keine Datenbank)
# ---------------------------------------------------------------------------
# Oeffnungszeiten je Wochentag (0=Mo ... 6=So), None = geschlossen
OEFFNUNG = {0: ("08:00", "21:00"), 1: ("08:00", "21:00"), 2: ("08:00", "21:00"),
            3: None, 4: ("08:00", "21:00"), 5: ("09:00", "21:00"),
            6: ("09:00", "21:00")}
MAX_PERSONEN = 8
TELEFON = "+41 33 822 08 31"
# Beispielhaft bereits belegte Zeit-Slots (Demo; echte Verwaltung = DBaaS-Ausbau)
BELEGT = ["12:00", "12:15", "18:00", "19:30"]

# Menue nach Kategorien (entspricht der Karte des Moon Cafe)
CATS = [
    {"key": "kaffee", "note": True, "items": [
        {"n": "Espresso", "p": 4.00}, {"n": "Americano", "p": 4.00},
        {"n": "Cappuccino", "p": 5.00}, {"n": "Flat White", "p": 5.50},
        {"n": "Caffè Latte", "p": 5.50}, {"n": "Vanille Latte", "p": 6.00, "en": "Vanilla Latte"}]},
    {"key": "matcha", "note": True, "items": [
        {"n": "Matcha Latte", "p": 6.00},
        {"n": "Erdbeer-Matcha-Latte", "p": 7.00, "en": "Strawberry Matcha Latte"},
        {"n": "Mango-Matcha-Latte", "p": 7.00, "en": "Mango Matcha Latte"}]},
    {"key": "tee", "items": [
        {"n": "Grüntee", "p": 4.50, "en": "Green Tea"}, {"n": "Jasmintee", "p": 4.50, "en": "Jasmine Tea"},
        {"n": "Earl Grey", "p": 4.50}, {"n": "English Breakfast", "p": 4.50},
        {"n": "Pfefferminztee", "p": 4.50, "en": "Peppermint Tea"},
        {"n": "Kamillentee", "p": 4.50, "en": "Chamomile Tea"},
        {"n": "Früchtetee", "p": 4.50, "en": "Fruit Tea"}]},
    {"key": "heiss", "items": [
        {"n": "Chai Latte", "p": 5.50}, {"n": "Heisse Schokolade", "p": 5.00, "en": "Hot Chocolate"}]},
    {"key": "kalt", "items": [
        {"n": "Coca-Cola", "p": 4.50}, {"n": "Coca-Cola Zero", "p": 4.50},
        {"n": "Sprite", "p": 4.50}, {"n": "Mineralwasser", "p": 4.50, "en": "Sparkling Water"},
        {"n": "Hausgemachter Eistee", "p": 5.00, "en": "Homemade Iced Tea"},
        {"n": "Pfirsich-Eistee", "p": 5.50, "en": "Peach Iced Tea"},
        {"n": "Yuzu-Limonade", "p": 5.50, "en": "Yuzu Lemonade"},
        {"n": "Frischer Orangensaft", "p": 5.50, "en": "Fresh Orange Juice"}]},
    {"key": "brunch", "items": [
        {"n": "Frühstücks-Bowl", "p": 13.50, "en": "Breakfast Bowl"},
        {"n": "Japanische Soufflé-Pancakes", "p": 16.50, "en": "Japanese Soufflé Pancakes"},
        {"n": "French Toast", "p": 15.50},
        {"n": "Avocado-Ei-Toast", "p": 16.50, "en": "Avocado & Egg Toast",
         "note_de": "mit Lachs + CHF 4.00", "note_en": "with salmon + CHF 4.00"},
        {"n": "Grilled Cheese Toast", "p": 14.50},
        {"n": "Salat mit gegrillten Crevetten", "p": 19.50, "en": "Grilled Prawn Salad"},
        {"n": "Früchte-Sando", "p": 11.50, "en": "Fruit Sando"},
        {"n": "Mungbohnen", "p": 8.50, "en": "Sweet Mung Beans"}]},
    {"key": "sandwich", "note_side": True, "items": [
        {"n": "Ei-Sandwich", "p": 8.50, "en": "Egg Sandwich"},
        {"n": "Thunfisch-Sandwich", "p": 9.50, "en": "Tuna Sandwich"},
        {"n": "Lachs-Sandwich", "p": 10.50, "en": "Salmon Sandwich"}]},
    {"key": "gebaeck", "items": [
        {"n": "Buttergipfeli", "p": 3.00, "en": "Butter Croissant"},
        {"n": "Pain au chocolat", "p": 3.80},
        {"n": "Butterbrötli", "p": 2.50, "en": "Butter Roll"},
        {"n": "Toast mit Butter & Konfitüre", "p": 5.50, "en": "Toast with Butter & Jam"}]},
    {"key": "kuchen", "items": [
        {"n": "Erdbeer-Shortcake", "p": 7.50, "en": "Strawberry Shortcake"},
        {"n": "Mango-Shortcake", "p": 7.50, "en": "Mango Shortcake"},
        {"n": "Shine-Muscat-Shortcake", "p": 8.50},
        {"n": "Schokoladen-Erdbeer-Shortcake", "p": 7.50, "en": "Chocolate Strawberry Shortcake"},
        {"n": "Himbeer-Roulade", "p": 6.50, "en": "Raspberry Roll Cake"}]},
    {"key": "glace", "items": [
        {"n": "Mövenpick Glace", "p": 4.50, "unit_de": "pro Kugel", "unit_en": "per scoop"}]},
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def phone_ok(raw):
    """Prueft eine Telefonnummer auf ein gueltiges Schweizer Format.

    Trennzeichen wie Leerschlag, Bindestrich oder Klammern werden zuerst
    entfernt. Akzeptiert werden nationale Nummern (0 + 9 Ziffern, z. B.
    0338220831) sowie die internationale Schreibweise (+41 oder 0041 + 9 Ziffern).
    Rueckgabe: True, wenn das Format gueltig ist, sonst False.
    """
    p = re.sub(r"[\s/().-]", "", raw or "")   # Trennzeichen entfernen
    return bool(re.match(r"^(0\d{9}|\+41\d{9}|0041\d{9})$", p))


# ---------------------------------------------------------------------------
# Uebersetzungen
# ---------------------------------------------------------------------------
T = {
    "de": {
        "title": "Moon Café Interlaken",
        "tagline": "Ein Café in Interlaken.",
        "open": "Jetzt geöffnet", "closed": "Zurzeit geschlossen",
        "about_t": "Über uns",
        "about_welcome": "Willkommen im Moon Café",
        "about": [
            "Mitten in Interlaken ist das Moon Café ein Ort für guten Kaffee, feinen Brunch und besondere Genussmomente. Inspiriert von moderner asiatischer Café-Kultur verbinden wir sorgfältig zubereitete Speisen und Getränke mit einem ästhetischen, gemütlichen und modernen Ambiente.",
            "Unsere Karte reicht von frisch zubereitetem Kaffee und cremigem Matcha bis zu Soufflé-Pancakes, French Toast, herzhaften Brunch-Gerichten und feinen Süssspeisen. Dabei stehen Qualität, frische Zutaten und eine liebevolle Zubereitung im Mittelpunkt.",
            "Auch das Ambiente ist Teil des Moon-Café-Erlebnisses. Ästhetisches Design, natürliche Materialien, warme Farben und liebevolle Details schaffen einen Ort, an dem man sich vom ersten Moment an wohlfühlt. Ob für einen ausgiebigen Brunch mit Freunden, eine entspannte Kaffeepause, ein gutes Buch oder einen ruhigen Nachmittag zum Lernen und Arbeiten, bei uns darf man ankommen, geniessen und gerne etwas länger bleiben.",
        ],
        "about_tag": "Good food. Brighter days. \u2615\uFE0F\U0001F950\U0001F319",
        "reserve": "Tisch reservieren", "menu": "Menü", "hours": "Öffnungszeiten",
        "contact": "Kontakt", "address": "Höheweg 20, 3800 Interlaken",
        "cat": {"kaffee": "Kaffee", "matcha": "Matcha", "tee": "Tee", "heiss": "Heissgetränke",
                "kalt": "Kalte Getränke", "brunch": "Ganztägiger Brunch", "sandwich": "Sandwiches",
                "gebaeck": "Gebäck", "kuchen": "Kuchen & Törtchen", "glace": "Glace"},
        "iced": "Auch als Iced erhältlich + CHF 0.50",
        "side": "Beilagen nach Wahl (Pommes Frites, Süsskartoffel-Pommes, Kleiner Salat) + CHF 4.00",
        "days": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        "closed_day": "geschlossen",
        "back": "Zurück zur Startseite", "r_title": "Tisch reservieren", "confirmed": "Reservierung bestätigt", "new_res": "Neue Reservierung",
        "ph_vorname": "Anna", "ph_nachname": "Muster", "ph_email": "anna.muster@beispiel.ch", "ph_phone": "+41 79 123 45 67", "ph_date": "TT.MM.JJJJ",
        "vorname": "Vorname", "nachname": "Nachname", "email": "E-Mail", "phone": "Handynummer",
        "date": "Datum", "time": "Uhrzeit", "pick_time": "Zeit wählen",
        "closed_this_day": "An diesem Tag geschlossen",
        "adults": "Erwachsene", "children": "Kinder",
        "highchair": "Kinderhochstuhl benötigt", "seat": "Sitzplatz",
        "inside": "Drinnen", "terrace": "Terrasse", "check": "Reservierung prüfen",
        "group_hint": "Für Gruppen ab " + str(MAX_PERSONEN + 1) + " Personen reservieren Sie bitte telefonisch unter " + TELEFON + ".",
        "note": "Hinweis: Diese Reservierung wird geprüft und bestätigt, in dieser "
                "Ausbaustufe jedoch nicht dauerhaft gespeichert.",
    },
    "en": {
        "title": "Moon Café Interlaken",
        "tagline": "A café in Interlaken.",
        "open": "Open now", "closed": "Currently closed",
        "about_t": "About us",
        "about_welcome": "Welcome to Moon Café",
        "about": [
            "Located in the heart of Interlaken, Moon Café is a place for great coffee, delicious brunch and special moments. Inspired by modern Asian café culture, we bring together carefully prepared food and drinks with an aesthetic, cosy and contemporary atmosphere.",
            "Our menu ranges from freshly brewed coffee and creamy matcha to soufflé pancakes, French toast, savoury brunch dishes and delicate sweets. Quality, fresh ingredients and thoughtful preparation are at the heart of everything we serve.",
            "The atmosphere is an essential part of the Moon Café experience. Aesthetic design, natural materials, warm tones and thoughtful details create a space where you can feel at ease from the moment you arrive. Whether you are joining friends for brunch, enjoying a quiet coffee, reading a good book, studying or working, Moon Café is a place to slow down, enjoy the moment and stay a little longer.",
        ],
        "about_tag": "Good food. Brighter days. \u2615\uFE0F\U0001F950\U0001F319",
        "reserve": "Reserve a table", "menu": "Menu", "hours": "Opening hours",
        "contact": "Contact", "address": "Höheweg 20, 3800 Interlaken",
        "cat": {"kaffee": "Coffee", "matcha": "Matcha", "tee": "Tea", "heiss": "Hot Drinks",
                "kalt": "Cold Drinks", "brunch": "All-Day Brunch", "sandwich": "Sandwiches",
                "gebaeck": "Bakery", "kuchen": "Cakes & Pastries", "glace": "Ice Cream"},
        "iced": "Also available iced + CHF 0.50",
        "side": "Choice of side (fries, sweet potato fries, small salad) + CHF 4.00",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "closed_day": "closed",
        "back": "Back to home", "r_title": "Reserve a table", "confirmed": "Reservation confirmed", "new_res": "New reservation",
        "ph_vorname": "Anna", "ph_nachname": "Smith", "ph_email": "anna.smith@example.com", "ph_phone": "+41 79 123 45 67", "ph_date": "DD.MM.YYYY",
        "vorname": "First name", "nachname": "Last name", "email": "E-mail", "phone": "Mobile number",
        "date": "Date", "time": "Time", "pick_time": "Select a time",
        "closed_this_day": "Closed on this day",
        "adults": "Adults", "children": "Children",
        "highchair": "High chair needed", "seat": "Seating",
        "inside": "Inside", "terrace": "Terrace", "check": "Check reservation",
        "group_hint": "For groups of " + str(MAX_PERSONEN + 1) + " or more, please call us at " + TELEFON + ".",
        "note": "Note: this reservation is validated and confirmed, but not permanently "
                "stored at this stage.",
    },
}


def get_lang():
    """Ermittelt die gewaehlte Sprache aus der Anfrage.

    Beruecksichtigt sowohl den URL-Parameter (?lang=en) als auch das
    versteckte Formularfeld. Standard ist Deutsch; nur "en" schaltet auf Englisch.
    """
    l = (request.args.get("lang") or request.form.get("lang") or "de").lower()
    return "en" if l == "en" else "de"


def ist_geoeffnet(jetzt=None):
    """Gibt zurueck, ob das Cafe zum uebergebenen Zeitpunkt geoeffnet ist.

    Liest die Oeffnungszeiten des jeweiligen Wochentags aus OEFFNUNG. Ist der
    Tag geschlossen (None), wird False zurueckgegeben; andernfalls wird geprueft,
    ob die aktuelle Uhrzeit innerhalb der Oeffnungszeiten liegt.
    """
    jetzt = jetzt or datetime.now()
    z = OEFFNUNG.get(jetzt.weekday())
    if not z:                       # an diesem Wochentag geschlossen
        return False
    return time.fromisoformat(z[0]) <= jetzt.time() <= time.fromisoformat(z[1])


def oeffnung_lesbar(lang):
    """Bereitet die Oeffnungszeiten fuer die Anzeige auf (je Sprache).

    Liefert eine Liste mit Wochentag und der lesbaren Zeitangabe
    (z. B. "08:00 - 21:00") beziehungsweise "geschlossen".
    """
    out = []
    for i, tag in enumerate(T[lang]["days"]):
        z = OEFFNUNG.get(i)
        out.append({"tag": tag, "zeiten": T[lang]["closed_day"] if not z else f"{z[0]} – {z[1]}"})
    return out


def menu_gruppen(lang):
    """Liefert das Menue nach Kategorien gruppiert fuer die Weboberflaeche.

    Je Eintrag werden Name (sprachabhaengig), Preis und optionale Zusaetze
    (Einheit, Hinweis) uebernommen. Zu ganzen Kategorien koennen Hinweise
    gehoeren (z. B. "auch als Iced" oder "Beilagen nach Wahl").
    """
    gr = []
    for c in CATS:
        items = []
        for m in c["items"]:
            name = m.get("en", m["n"]) if lang == "en" else m["n"]
            it = {"name": name, "preis": m["p"]}
            if "unit_de" in m:
                it["unit"] = m["unit_en"] if lang == "en" else m["unit_de"]
            if "note_de" in m:
                it["inote"] = m["note_en"] if lang == "en" else m["note_de"]
            items.append(it)
        note = None
        if c.get("note"):
            note = T[lang]["iced"]
        elif c.get("note_side"):
            note = T[lang]["side"]
        gr.append({"titel": T[lang]["cat"][c["key"]], "items": items, "note": note})
    return gr


def menu_flach(lang):
    """Liefert das Menue als flache Liste fuer das Web-API (/api/menu).

    Anders als menu_gruppen() ohne Verschachtelung: je Eintrag Name,
    Kategorie und Preis, direkt als JSON ausgebbar.
    """
    out = []
    for c in CATS:
        for m in c["items"]:
            name = m.get("en", m["n"]) if lang == "en" else m["n"]
            out.append({"name": name, "kategorie": T[lang]["cat"][c["key"]], "preis_chf": m["p"]})
    return out


def slots_fuer(weekday):
    """15-Minuten-Slots innerhalb der Oeffnungszeiten (ohne belegte)."""
    z = OEFFNUNG.get(weekday)
    if not z:
        return []
    oh, om = map(int, z[0].split(":"))
    ch, cm = map(int, z[1].split(":"))
    t, end = oh * 60 + om, ch * 60 + cm
    out = []
    while t < end:
        s = f"{t // 60:02d}:{t % 60:02d}"
        if s not in BELEGT:
            out.append(s)
        t += 15
    return out


# ---------------------------------------------------------------------------
# Design (modern, ruhig, responsiv)
# ---------------------------------------------------------------------------
# Favicon wird als Datei aus /static ausgeliefert (siehe head()).

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@300;400;500&display=swap');
:root{
  --bg:#f3ede3; --bg2:#ece3d5; --card:#fdfbf7; --ink:#33302b; --muted:#948b7d;
  --line:#e6ddcd; --accent:#a9865f; --accent2:#8f9a84; --ok:#5c7d55; --warn:#b0654e;
  --shadow:0 6px 24px rgba(80,66,45,.07);
}
*{box-sizing:border-box}
html,body{margin:0}
body{color:var(--ink);font-family:'Inter',system-ui,sans-serif;
  font-weight:300;line-height:1.7;-webkit-font-smoothing:antialiased;
  background:
    radial-gradient(900px 520px at 12% -8%, #f8f2e8 0, rgba(248,242,232,0) 60%),
    radial-gradient(820px 480px at 108% 6%, #efe4d1 0, rgba(239,228,209,0) 55%),
    radial-gradient(700px 700px at 50% 120%, #ece1cf 0, rgba(236,225,207,0) 60%),
    linear-gradient(180deg,#f3ede2 0,#ece2d1 100%);
  background-attachment:fixed;}
.wrap{max-width:860px;margin:0 auto;padding:1.2rem 1.15rem 4rem;}
.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;}
.brand{display:flex;align-items:center;gap:.6rem;}
.brand .logo{width:32px;height:32px;object-fit:contain}
.brand h1{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:1.7rem;margin:0;
  letter-spacing:1px;text-transform:uppercase;}
.lang a{color:var(--muted);text-decoration:none;font-size:.82rem;padding:.15rem .3rem;letter-spacing:.03em;}
.lang a.on{color:var(--ink);border-bottom:1.5px solid var(--accent);}
.hero{position:relative;text-align:center;padding:3rem 1.2rem 2.6rem;margin:.7rem 0 1.4rem;
  border-radius:26px;overflow:hidden;
  background:radial-gradient(130% 100% at 50% -20%,var(--bg2) 0,var(--bg) 72%);}
.hero .moon{margin-bottom:.5rem}
.hero .name{font-family:'Cormorant Garamond',serif;font-size:2.5rem;font-weight:700;
  letter-spacing:5px;text-transform:uppercase;margin:.2rem 0 .1rem;}
.hero .sub{color:var(--muted);letter-spacing:.14em;text-transform:uppercase;font-size:.72rem;margin:0 0 1.2rem;}
.badge{display:inline-flex;align-items:center;gap:.45rem;padding:.32rem .85rem;border-radius:999px;
  font-size:.8rem;font-weight:500;}
.badge.open{background:#e7efe2;color:var(--ok);} .badge.closed{background:#f3e5df;color:var(--warn);}
.dot{width:.5rem;height:.5rem;border-radius:50%;background:currentColor;}
.cta{margin-top:1.5rem;display:flex;gap:.6rem;justify-content:center;flex-wrap:wrap;}
.btn{display:inline-block;background:var(--accent);color:#fff;border:0;border-radius:12px;
  padding:.72rem 1.4rem;font-size:1rem;font-family:inherit;text-decoration:none;cursor:pointer;
  transition:opacity .2s;} .btn:hover{opacity:.9}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent);}
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;
  padding:1.6rem 1.7rem;margin:1.2rem 0;box-shadow:var(--shadow);}
h2{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:1.7rem;text-align:center;margin:.1rem 0 1.4rem;}
.menuhead{text-align:center;margin-bottom:1.4rem}
.herologo{width:92px;height:92px;object-fit:contain;display:block;margin:0 auto 1rem}
.menulogo{width:66px;height:66px;object-fit:contain;display:block;margin:0 auto .2rem}
.menuname{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:1.7rem;letter-spacing:4px;text-transform:uppercase}
.menusub{color:var(--muted);letter-spacing:.16em;text-transform:uppercase;font-size:.68rem;margin-top:.1rem}
.center{text-align:center;color:var(--muted);max-width:38rem;margin:0 auto;}
.mgrid{display:grid;grid-template-columns:1fr 1fr;gap:1.4rem 2.4rem;}
.mcat h3{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:1.15rem;letter-spacing:.06em;
  text-transform:uppercase;margin:.2rem 0 .5rem;color:var(--ink);border-bottom:1px solid var(--line);padding-bottom:.3rem;}
.mrow{display:flex;justify-content:space-between;gap:1rem;padding:.24rem 0;}
.mrow .nm{color:var(--ink)} .mrow .pr{color:var(--muted);white-space:nowrap}
.inote{display:block;color:var(--accent);font-size:.8rem;}
.mnote{color:var(--accent2);font-size:.8rem;margin-top:.5rem;font-style:italic;}
table.hours{width:100%;max-width:22rem;margin:0 auto;border-collapse:collapse;}
table.hours td{padding:.4rem 0;border-bottom:1px solid var(--line);}
table.hours td.r{text-align:right;color:var(--muted);}
table.hours tr:last-child td{border-bottom:0}
.contact{text-align:center;color:var(--muted);}
.contact a{color:var(--accent);text-decoration:none;font-weight:500}
footer{color:var(--muted);font-size:.8rem;text-align:center;margin-top:2rem;}
nav a{color:var(--accent);text-decoration:none;font-size:.95rem;}
label{display:block;margin:.75rem 0 .28rem;font-size:.9rem;color:var(--muted);}
input::placeholder{color:#b9b0a2;opacity:1}
input,select{width:100%;padding:.65rem .7rem;border:1px solid var(--line);border-radius:11px;
  font-size:1rem;font-family:inherit;background:#fff;color:var(--ink);}
input:focus,select:focus{outline:none;border-color:var(--accent);}
input:user-invalid,select:user-invalid{border-color:var(--warn);background:#fdf3f0;}
select:disabled{background:#f4efe6;color:#b6ad9d}
.row{display:flex;gap:.9rem;flex-wrap:wrap;} .row>div{flex:1;min-width:140px;}
.check{display:flex;align-items:center;gap:.55rem;margin-top:.9rem;cursor:pointer;color:var(--ink)}
.check input{width:auto}
.hint{color:var(--muted);font-size:.82rem;margin-top:.35rem}
.result{margin-top:1.2rem;padding:1.05rem 1.15rem;border-radius:13px;font-size:.98rem;white-space:pre-line;line-height:1.75;}
.result.ok{background:#e7efe2;color:var(--ok);} .result.err{background:#f3e5df;color:var(--warn);}
code{background:#eae1d2;padding:2px 7px;border-radius:6px;}
/* flatpickr Akzentfarbe */
.flatpickr-day.selected,.flatpickr-day.selected:hover{background:var(--accent);border-color:var(--accent);}
.flatpickr-day.today{border-color:var(--accent2);}
@media (max-width:640px){
  .wrap{padding:1rem .9rem 3rem}
  .hero{padding:2.3rem 1rem 2rem}
  .hero .name{font-size:2rem;letter-spacing:3px}
  .mgrid{grid-template-columns:1fr;gap:1.2rem}
  .card{padding:1.3rem 1.2rem;border-radius:16px}
  h2{font-size:1.45rem}
}
"""

LOGO = "<img class='logo' src='/static/favicon.png' alt='Moon Café'>"
MOON_HERO = ("<svg class='moon' width='54' height='54' viewBox='0 0 100 100'>"
             "<g transform='rotate(-18 50 50)'><path d='M60 6 A46 46 0 1 0 60 94 A36 36 0 1 1 60 6 Z' fill='#c1a06a'/></g></svg>")


def head(t):
    """Baut den HTML-Kopf (head) mit Titel, Viewport und Favicon.

    Der Viewport-Eintrag sorgt fuer die mobile Darstellung, das Favicon wird
    aus dem statischen Ordner geladen, und der Seitentitel (t) erscheint im
    Browser-Tab.
    """
    return (f"<head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<link rel='icon' type='image/png' href='/static/favicon.png'>"
            f"<title>{t}</title><style>{CSS}</style></head>")


def topbar(page, lang):
    """Erzeugt die obere Leiste mit Logo und Sprachumschaltung (DE/EN).

    "page" ist die aktuelle Seite (fuer die Sprachlinks), "lang" die aktive
    Sprache, die im Umschalter hervorgehoben wird.
    """
    def a(code, label):
        cls = "on" if lang == code else ""
        return f"<a class='{cls}' href='/{page}?lang={code}'>{label}</a>"
    return (f"<div class='top'><div class='brand'>{LOGO}<h1>Moon Café</h1></div>"
            f"<div class='lang'>{a('de','DE')}<span style='color:#cbc3b5'>/</span>{a('en','EN')}</div></div>")


START = """
<!doctype html><html lang="{{lang}}">{{head|safe}}<body><div class="wrap">
{{top|safe}}
<section class="hero">
  <img src="/static/favicon.png" alt="Moon Café" class="herologo">
  <div class="sub">Coffee · Brunch · Sweets</div>
  <div class="cta">
    <a class="btn" href="/reservieren?lang={{lang}}">{{t.reserve}}</a>
    <a class="btn ghost" href="/menu?lang={{lang}}">{{t.menu}}</a>
  </div>
</section>

<div class="card"><h2>{{t.about_t}}</h2>
  <p class="center" style="font-family:'Cormorant Garamond',serif;font-size:1.35rem;color:var(--ink);margin-bottom:1rem">{{t.about_welcome}}</p>
  {% for p in t.about %}<p class="center" style="margin-bottom:.9rem">{{p}}</p>{% endfor %}
  <p class="center" style="font-style:italic;color:var(--accent);margin-top:1.1rem">{{t.about_tag}}</p>
</div>

<div class="card"><h2>{{t.hours}}</h2>
  <div style="text-align:center;margin-bottom:1.1rem">
    {% if offen %}<span class="badge open"><span class="dot"></span>{{t.open}}</span>
    {% else %}<span class="badge closed"><span class="dot"></span>{{t.closed}}</span>{% endif %}
  </div>
  <table class="hours">{% for o in oeffnung %}<tr><td>{{o.tag}}</td><td class="r">{{o.zeiten}}</td></tr>{% endfor %}</table>
</div>

<div class="card"><h2>{{t.contact}}</h2>
  <p class="contact">{{t.address}}<br>{{tel}}</p>
</div>

<footer>
  <div style="border-top:1px solid var(--line);margin-top:1.5rem;padding-top:1.2rem">
    © 2026 Moon Café Interlaken – Praxisarbeit VICC – Shahilla Fazal
  </div>
</footer>
</div></body></html>
"""


MENU_SEITE = """
<!doctype html><html lang="{{lang}}">{{head|safe}}<body><div class="wrap">
{{top|safe}}
<nav style="margin:.5rem 0 .2rem"><a href="/?lang={{lang}}">← {{t.back}}</a></nav>
<div class="card" id="menu">
  <div class="menuhead">
    <img src="/static/favicon.png" alt="Moon Café" class="menulogo">
    <div class="menusub">Coffee · Brunch · Sweets</div>
  </div>
  <div class="mgrid">
  {% for g in gruppen %}
    <div class="mcat">
      <h3>{{g.titel}}</h3>
      {% for m in g["items"] %}
        <div class="mrow"><span class="nm">{{m.name}}{% if m.unit %} <small style="color:#948b7d">{{m.unit}}</small>{% endif %}</span>
        <span class="pr">CHF {{ '%.2f'|format(m.preis) }}</span></div>
        {% if m.inote %}<span class="inote">{{m.inote}}</span>{% endif %}
      {% endfor %}
      {% if g.note %}<div class="mnote">{{g.note}}</div>{% endif %}
    </div>
  {% endfor %}
  </div>
</div>
<p style="text-align:center;margin-top:1.4rem"><a class="btn" href="/reservieren?lang={{lang}}">{{t.reserve}}</a></p>
<footer>
  <div style="border-top:1px solid var(--line);margin-top:1.5rem;padding-top:1.2rem">
    © 2026 Moon Café Interlaken – Praxisarbeit VICC – Shahilla Fazal
  </div>
</footer>
</div></body></html>
"""

RESERVIEREN = """
<!doctype html><html lang="{{lang}}">{{head|safe}}
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
<body><div class="wrap">
{{top|safe}}
{% if ergebnis and ergebnis.ok %}
<div class="card">
  <div style="text-align:center;margin-bottom:.4rem">
    <svg width="52" height="52" viewBox="0 0 52 52" fill="none"><circle cx="26" cy="26" r="24" fill="#e7efe2"/>
    <path d="M17 27l6 6 12-13" stroke="#5c7d55" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <h2 style="margin:.5rem 0 0">{{t.confirmed}}</h2>
  </div>
  <div class="result ok">{{ ergebnis.text }}</div>
  <p style="text-align:center;margin-top:1.4rem">
    <a class="btn" href="/?lang={{lang}}">{{t.back}}</a>
  </p>
</div>
{% else %}
<nav style="margin:.5rem 0 .2rem"><a href="/?lang={{lang}}">← {{t.back}}</a></nav>
<div class="card">
  <h2 style="text-align:left">{{t.r_title}}</h2>
  <form method="post">
    <input type="hidden" name="lang" value="{{lang}}">
    <div class="row">
      <div><label>{{t.vorname}}</label><input name="vorname" placeholder="{{t.ph_vorname}}" value="{{ form.get('vorname','') }}" required></div>
      <div><label>{{t.nachname}}</label><input name="nachname" placeholder="{{t.ph_nachname}}" value="{{ form.get('nachname','') }}" required></div>
    </div>
    <div class="row">
      <div><label>{{t.email}}</label><input type="email" name="email" placeholder="{{t.ph_email}}" value="{{ form.get('email','') }}" required></div>
      <div><label>{{t.phone}}</label><input type="tel" name="telefon" placeholder="{{t.ph_phone}}"
        pattern="(\\+41|0041|0)[\\s0-9]{9,13}"
        value="{{ form.get('telefon','') }}" required></div>
    </div>
    <div class="row">
      <div><label>{{t.date}}</label><input id="datum" name="datum" placeholder="{{t.ph_date}}" 
        value="{{ form.get('datum','') }}" required></div>
      <div><label>{{t.time}}</label>
        <select id="zeit" name="zeit" required disabled><option value="">{{t.pick_time}}</option></select></div>
    </div>
    <div class="row">
      <div><label>{{t.adults}}</label><input type="number" name="erwachsene" min="1" max="{{maxp}}"
        value="{{ form.get('erwachsene','2') }}" required></div>
      <div><label>{{t.children}}</label><input type="number" name="kinder" min="0" max="{{maxp}}"
        value="{{ form.get('kinder','0') }}"></div>
    </div>
    <div class="hint">{{t.group_hint}}</div>
    <label class="check"><input type="checkbox" name="kinderstuhl" value="ja"
      {{ 'checked' if form.get('kinderstuhl')=='ja' else '' }}> {{t.highchair}}</label>
    <label>{{t.seat}}</label>
    <select name="bereich">
      <option value="drinnen" {{ 'selected' if form.get('bereich')=='drinnen' else '' }}>{{t.inside}}</option>
      <option value="terrasse" {{ 'selected' if form.get('bereich')=='terrasse' else '' }}>{{t.terrace}}</option>
    </select>
    <p style="margin-top:1.3rem"><button class="btn" type="submit">{{t.check}}</button></p>
  </form>
  {% if ergebnis %}<div class="result err">{{ ergebnis.text }}</div>{% endif %}
</div>
{% endif %}
<footer>
  <div style="border-top:1px solid var(--line);margin-top:1.2rem;padding-top:1.2rem">
    © 2026 Moon Café Interlaken – Praxisarbeit VICC – Shahilla Fazal
  </div>
</footer>
</div>
{% if not (ergebnis and ergebnis.ok) %}
<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
<script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/de.js"></script>
<script>
const OPEN={{ open_json|safe }};const BOOKED={{ booked_json|safe }};const LANG="{{lang}}";
const TXT={pick:"{{t.pick_time}}",closed:"{{t.closed_this_day}}"};
const timeSel=document.getElementById('zeit');
function pad(n){return String(n).padStart(2,'0');}
function build(dateStr,keep){
  timeSel.innerHTML='';
  if(!dateStr){timeSel.disabled=true;const o=document.createElement('option');o.value='';o.textContent=TXT.pick;timeSel.appendChild(o);return;}
  const d=new Date(dateStr+'T00:00:00');const key=(d.getDay()+6)%7;const hrs=OPEN[key];
  if(!hrs){timeSel.disabled=true;const o=document.createElement('option');o.value='';o.textContent=TXT.closed;timeSel.appendChild(o);return;}
  timeSel.disabled=false;
  const f=document.createElement('option');f.value='';f.textContent=TXT.pick;timeSel.appendChild(f);
  const [oh,om]=hrs[0].split(':').map(Number);const [ch,cm]=hrs[1].split(':').map(Number);
  let t=oh*60+om;const end=ch*60+cm;
  // heute: vergangene Zeiten (inkl. kleiner Vorlaufzeit) ausblenden
  const now=new Date();
  const isToday=(d.getFullYear()===now.getFullYear()&&d.getMonth()===now.getMonth()&&d.getDate()===now.getDate());
  const minToday=isToday?(now.getHours()*60+now.getMinutes()+15):-1;
  for(;t<end;t+=15){const s=pad(Math.floor(t/60))+':'+pad(t%60);if(BOOKED.includes(s))continue;
    if(t<=minToday)continue;
    const o=document.createElement('option');o.value=s;o.textContent=s;if(s===keep)o.selected=true;timeSel.appendChild(o);}
}
flatpickr('#datum',{locale:LANG==='de'?'de':'default',minDate:'today',maxDate:new Date().fp_incr(365),dateFormat:'Y-m-d',altInput:true,
  altFormat:'d.m.Y',
  disable:[function(d){return d.getDay()===4;}],
  onChange:function(s,ds){build(ds,'');}});
document.addEventListener('DOMContentLoaded',function(){
  const dv=document.getElementById('datum').value;if(dv){build(dv,"{{ form.get('zeit','') }}");}});

(function(){
  const M={de:{req:"Bitte füllen Sie dieses Feld aus.",email:"Bitte geben Sie eine gültige E-Mail-Adresse ein.",tel:"Bitte geben Sie eine gültige Telefonnummer ein (z. B. 033 822 08 31)."},
           en:{req:"Please fill in this field.",email:"Please enter a valid e-mail address.",tel:"Please enter a valid phone number (e.g. 033 822 08 31)."}}[LANG]||{};
  const form=document.querySelector('form');
  form.querySelectorAll('input,select').forEach(function(el){
    el.addEventListener('invalid',function(){
      if(el.validity.valueMissing)el.setCustomValidity(M.req);
      else if(el.validity.typeMismatch)el.setCustomValidity(el.type==='email'?M.email:M.req);
      else if(el.validity.patternMismatch)el.setCustomValidity(M.tel);
      else el.setCustomValidity('');
    });
    el.addEventListener('input',function(){el.setCustomValidity('');});
    el.addEventListener('change',function(){el.setCustomValidity('');});
  });
})();
</script>
{% endif %}
</body></html>
"""


@app.route("/")
def startseite():
    """Startseite: Vorstellung, Menue, Oeffnungszeiten und Status.

    Ermittelt die Sprache, prueft mit ist_geoeffnet(), ob gerade geoeffnet ist,
    und uebergibt Menue und Oeffnungszeiten an die HTML-Vorlage.
    """
    lang = get_lang()
    return render_template_string(
        START, head=head(T[lang]["title"]), top=topbar("", lang),
        t=T[lang], lang=lang, offen=ist_geoeffnet(), moon=MOON_HERO,
        gruppen=menu_gruppen(lang), oeffnung=oeffnung_lesbar(lang),
        tel=TELEFON, tel_clean=re.sub(r"\s", "", TELEFON))


@app.route("/menu")
def menu_seite():
    """Menükarte als eigene Seite, nach Kategorien gruppiert."""
    lang = get_lang()
    return render_template_string(
        MENU_SEITE, head=head(T[lang]["menu"] + " - Moon Café"), top=topbar("menu", lang),
        t=T[lang], lang=lang, gruppen=menu_gruppen(lang))


@app.route("/reservieren", methods=["GET", "POST"])
def reservieren():
    """Reservierungsseite: zeigt das Formular (GET) und prueft es (POST).

    Bei einem Absenden (POST) wird pruefe() aufgerufen; bei Erfolg erscheint die
    Bestaetigung ohne Formular. Die Oeffnungszeiten und die belegten Zeiten
    werden als JSON an die Seite uebergeben, damit das Datums- und Zeitfeld nur
    gueltige Werte anbietet.
    """
    import json
    lang = get_lang()
    ergebnis = pruefe(request.form, lang) if request.method == "POST" else None
    open_map = {i: OEFFNUNG[i] for i in range(7)}
    open_json = json.dumps({str(k): (list(v) if v else None) for k, v in open_map.items()})
    return render_template_string(
        RESERVIEREN, head=head(T[lang]["r_title"] + " - Moon Café"), top=topbar("reservieren", lang),
        t=T[lang], lang=lang, form=request.form, maxp=MAX_PERSONEN, ergebnis=ergebnis,
        open_json=open_json, booked_json=json.dumps(BELEGT))


def pruefe(form, lang):
    """Prueft die Reservierungseingaben serverseitig und bildet die Antwort.

    Geprueft werden der Reihe nach: Vor- und Nachname, E-Mail-Format,
    Telefonformat, gueltiges Datum/Personenzahl, Datum nicht in der
    Vergangenheit und hoechstens ein Jahr im Voraus, Oeffnungstag, verfuegbare
    Uhrzeit (inkl. belegter Zeiten) sowie mindestens eine erwachsene Person und
    die maximale Personenzahl. Bei einem Fehler wird eine verstaendliche
    Meldung zurueckgegeben (ok=False), sonst eine Bestaetigung mit allen
    Reservierungsdetails (ok=True). Die Meldungen sind zweisprachig (m()-Helfer).
    Hinweis: Die Reservierung wird in dieser Ausbaustufe geprueft und
    bestaetigt, aber nicht dauerhaft gespeichert (Persistenz = DBaaS-Ausbau).
    """
    de = lang == "de"
    def m(a, b): return a if de else b   # waehlt die deutsche oder englische Meldung
    vorname = (form.get("vorname") or "").strip()
    nachname = (form.get("nachname") or "").strip()
    email = (form.get("email") or "").strip()
    telefon = (form.get("telefon") or "").strip()
    if not vorname or not nachname:
        return {"ok": False, "text": m("Bitte Vor- und Nachnamen angeben.", "Please enter your first and last name.")}
    if not EMAIL_RE.match(email):
        return {"ok": False, "text": m("Bitte eine gültige E-Mail-Adresse angeben.", "Please enter a valid e-mail address.")}
    if not phone_ok(telefon):
        return {"ok": False, "text": m("Bitte eine gültige Telefonnummer angeben (z. B. 033 822 08 31).",
                                       "Please enter a valid phone number (e.g. 033 822 08 31).")}
    try:
        d = date.fromisoformat(form.get("datum", ""))
        erwachsene = int(form.get("erwachsene", "0"))
        kinder = int(form.get("kinder", "0") or "0")
    except ValueError:
        return {"ok": False, "text": m("Bitte Datum und Personenzahl korrekt angeben.", "Please enter a valid date and number of guests.")}
    zeit = form.get("zeit", "")
    if d < date.today():
        return {"ok": False, "text": m("Das gewählte Datum liegt in der Vergangenheit.", "The selected date is in the past.")}
    from datetime import timedelta
    if d > date.today() + timedelta(days=365):
        return {"ok": False, "text": m("Reservierungen sind höchstens ein Jahr im Voraus möglich.",
                                       "Reservations can be made up to one year in advance.")}
    if OEFFNUNG.get(d.weekday()) is None:
        return {"ok": False, "text": m(f"Am {T['de']['days'][d.weekday()]} ist das Moon Café geschlossen.",
                                       f"Moon Café is closed on {T['en']['days'][d.weekday()]}.")}
    if zeit not in slots_fuer(d.weekday()):
        return {"ok": False, "text": m("Bitte eine verfügbare Uhrzeit wählen.", "Please choose an available time.")}
    if d == date.today():
        now = datetime.now()
        zt = time.fromisoformat(zeit)
        if (zt.hour * 60 + zt.minute) <= (now.hour * 60 + now.minute):
            return {"ok": False, "text": m("Diese Uhrzeit liegt bereits in der Vergangenheit. Bitte eine spätere Zeit wählen.",
                                           "This time is already in the past. Please choose a later time.")}
    if erwachsene < 1:
        return {"ok": False, "text": m("Für eine Reservierung wird mindestens eine erwachsene Person benötigt.", "At least one adult is required.")}
    personen = erwachsene + kinder
    if not (1 <= personen <= MAX_PERSONEN):
        return {"ok": False, "text": m(f"Wir nehmen Reservierungen für 1 bis {MAX_PERSONEN} Personen entgegen. {T['de']['group_hint']}",
                                       f"We accept reservations for 1 to {MAX_PERSONEN} guests. {T['en']['group_hint']}")}
    # Bestaetigung
    if de:
        teile = [f"{erwachsene} {'Erwachsener' if erwachsene==1 else 'Erwachsene'}"]
        if kinder: teile.append(f"{kinder} {'Kind' if kinder==1 else 'Kinder'}")
        wer = " und ".join(teile)
        bereich = "Terrasse" if form.get("bereich") == "terrasse" else "Innenbereich"
        stuhl = "ja" if form.get("kinderstuhl") == "ja" else "nein"
        text = (
            f"Vielen Dank für Ihre Reservierung, {vorname} {nachname}. "
            f"Wir haben Ihre Anfrage erfolgreich entgegengenommen. Hier Ihre Reservierungsdetails:\n"
            f"• Name: {vorname} {nachname}\n"
            f"• Datum: {d.strftime('%d.%m.%Y')} um {zeit} Uhr\n"
            f"• Personen: {wer}\n"
            f"• Sitzplatz: {bereich}\n"
            f"• Kinderhochstuhl: {stuhl}\n"
            f"• Kontakt: {email}, {telefon}\n"
            f"Bitte beachten Sie: Reservierte Tische werden bei einer Verspätung von mehr als "
            f"15 Minuten nicht mehr garantiert. Wir bitten um Verständnis. "
            f"Wir freuen uns sehr auf Ihren Besuch und wünschen Ihnen bis dahin eine schöne Zeit. "
            f"Bis bald im Moon Café!")
    else:
        teile = [f"{erwachsene} adult" + ("s" if erwachsene != 1 else "")]
        if kinder: teile.append(f"{kinder} child" + ("ren" if kinder != 1 else ""))
        wer = " and ".join(teile)
        bereich = "Terrace" if form.get("bereich") == "terrasse" else "Inside"
        stuhl = "yes" if form.get("kinderstuhl") == "ja" else "no"
        text = (
            f"Thank you for your reservation, {vorname} {nachname}. "
            f"We have successfully received your request. Here are your reservation details:\n"
            f"• Name: {vorname} {nachname}\n"
            f"• Date: {d.strftime('%d.%m.%Y')} at {zeit}\n"
            f"• Guests: {wer}\n"
            f"• Seating: {bereich}\n"
            f"• High chair: {stuhl}\n"
            f"• Contact: {email}, {telefon}\n"
            f"Please note: reserved tables are no longer guaranteed after a delay of more than "
            f"15 minutes. Thank you for your understanding. "
            f"We very much look forward to your visit. See you soon at Moon Café!")
    return {"ok": True, "text": text}


# ---------------------------------------------------------------------------
# Web-API (JSON)
# ---------------------------------------------------------------------------
@app.route("/favicon.ico")
def favicon():
    """Liefert das Favicon auch unter dem Standardpfad /favicon.ico."""
    from flask import send_from_directory
    return send_from_directory("static", "favicon.png", mimetype="image/png")


@app.route("/api/status")
def api_status():
    """Web-API: Betriebsstatus als JSON (ob geoeffnet, Zeit, Instanz)."""
    return jsonify({"betrieb": "Moon Café Interlaken", "status": "ok",
                    "geoeffnet": ist_geoeffnet(),
                    "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "instanz": os.getenv("WEBSITE_INSTANCE_ID", "lokal")})


@app.route("/api/menu")
def api_menu():
    """Web-API: liefert die Menükarte als JSON."""
    return jsonify(menu_flach(get_lang()))


@app.route("/api/oeffnung")
def api_oeffnung():
    """Web-API: liefert die Oeffnungszeiten als JSON."""
    return jsonify(oeffnung_lesbar(get_lang()))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
