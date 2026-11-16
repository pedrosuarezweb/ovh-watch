#!/usr/bin/env python3
"""
Vigila el stock del VPS-3 2027 de OVHcloud en datacenters de Europa y avisa
por WhatsApp y email cuando aparece disponible.

Uso:
  python3 ovh_vps_watch.py --list      # muestra los planCode VPS 2027 del catálogo
  python3 ovh_vps_watch.py             # comprueba stock (para el cron)
  python3 ovh_vps_watch.py --test      # envía un aviso de prueba

Solo usa la librería estándar de Python 3.
"""
import json, os, smtplib, sys, urllib.parse, urllib.request
from email.message import EmailMessage

# ---------------- CONFIGURACIÓN ----------------
SUBSIDIARY = "ES"
PLAN_CODE = os.getenv("OVH_PLAN_CODE", "")          # ej. el que salga con --list
# Códigos de datacenter europeos que se consideran válidos
EUROPE = {"GRA", "SBG", "RBX", "WAW", "DE", "LIM", "UK", "ERI",
          "EU-WEST-MAD", "EU-SOUTH-MIL", "EU-WEST-PAR"}

# WhatsApp vía CallMeBot (apikey gratuita, ver instrucciones)
WA_PHONE = os.getenv("WA_PHONE", "")
WA_APIKEY = os.getenv("WA_APIKEY", "")

# Email (opcional)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")   # varios separados por comas

STATE_FILE = os.getenv("STATE_FILE") or os.path.expanduser("~/.ovh_vps_watch_state.json")
API = "https://eu.api.ovh.com/v1"
ORDER_URL = "https://www.ovhcloud.com/es-es/vps/"
# ------------------------------------------------


def get(path, **params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ovh-vps-watch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def list_plans():
    cat = get("/order/catalog/public/vps", ovhSubsidiary=SUBSIDIARY)
    for p in cat.get("plans", []):
        code = p.get("planCode", "")
        name = p.get("invoiceName", "")
        if "2027" in code or "2027" in name:
            print(f"{code:40} {name}")


def available_dcs():
    data = get("/vps/order/rule/datacenter",
               ovhSubsidiary=SUBSIDIARY, planCode=PLAN_CODE)
    hits = []
    for dc in data.get("datacenters", []):
        code = dc.get("datacenter", "")
        statuses = [v for k, v in dc.items() if k.lower().endswith("status")]
        if code.upper() in EUROPE and any(s == "available" for s in statuses):
            hits.append(code)
    return sorted(hits)


def notify(text):
    sent = False
    if WA_PHONE and WA_APIKEY:
        q = urllib.parse.urlencode({"phone": WA_PHONE, "text": text, "apikey": WA_APIKEY})
        urllib.request.urlopen(f"https://api.callmebot.com/whatsapp.php?{q}", timeout=30)
        sent = True
    if SMTP_HOST and SMTP_USER and MAIL_TO:
        msg = EmailMessage()
        msg["Subject"] = "OVH: VPS-3 2027 disponible"
        msg["From"] = SMTP_USER
        msg["To"] = ", ".join(m.strip() for m in MAIL_TO.split(","))
        msg.set_content(text)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        sent = True
    if not sent:
        print("Sin canal de aviso configurado:\n" + text)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"available": []}


def main():
    if "--list" in sys.argv:
        return list_plans()
    if "--test" in sys.argv:
        return notify("Prueba del vigilante de stock OVH ✅")
    if not PLAN_CODE:
        sys.exit("Falta OVH_PLAN_CODE. Ejecuta primero con --list.")

    now = available_dcs()
    prev = load_state().get("available", [])
    new = [d for d in now if d not in prev]
    if new:
        notify(f"🟢 VPS-3 2027 DISPONIBLE en: {', '.join(new)}\n{ORDER_URL}")
    with open(STATE_FILE, "w") as f:
        json.dump({"available": now}, f)
    print("Disponibles:", now or "ninguno")


if __name__ == "__main__":
    main()
