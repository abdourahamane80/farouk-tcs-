import sqlite3,random,string,datetime,requests,urllib.parse,os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
app=FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

BOT_TOKEN="8718051134:AAE2dXW7M1a1vTtCjfy-Qy_rAWa7WY1wfrQ"
CHAT_ID="1187788046"
WAPP_PHONE="22793258430"
WAPP_APIKEY="1888207"
PWD="Safiya80"

DB_PATH="/var/data/tickets.db" if os.path.exists("/var/data") else "tickets.db"

def send_telegram(msg):
 try:
  requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"},timeout=5)
 except:
  pass
def send_whatsapp(msg):
 try:
  requests.get(f"https://api.callmebot.com/whatsapp.php?phone={WAPP_PHONE}&text={urllib.parse.quote(msg)}&apikey={WAPP_APIKEY}",timeout=10)
 except:
  pass
def send_all(tg,w):
 send_telegram(tg)
 send_whatsapp(w)

PLANS={
"2h":{"nom":"2 HEURES","prix":50,"duree_str":"2 Heures","hours":2},
"7h":{"nom":"7 HEURES","prix":100,"duree_str":"7 Heures","hours":7},
"1j":{"nom":"1 JOUR","prix":150,"duree_str":"24 Heures","hours":24},
"2j":{"nom":"2 JOURS","prix":300,"duree_str":"2 Jours","hours":48},
"1sem":{"nom":"1 SEMAINE","prix":500,"duree_str":"7 Jours","hours":168},
"2sem":{"nom":"2 SEMAINES","prix":800,"duree_str":"14 Jours","hours":336},
"1mois":{"nom":"1 MOIS","prix":1500,"duree_str":"30 Jours","hours":720},
"famille":{"nom":"1 MOIS FAMILLE","prix":0,"duree_str":"30 Jours GRATUIT","hours":720}
}

def init_db():
 conn=sqlite3.connect(DB_PATH)
 conn.execute("CREATE TABLE IF NOT EXISTS tickets (code TEXT PRIMARY KEY, plan TEXT, prix INTEGER, nom TEXT, created TEXT, first_use TEXT, expire TEXT)")
 try:conn.execute("ALTER TABLE tickets ADD COLUMN first_use TEXT")
 except:pass
 try:conn.execute("ALTER TABLE tickets ADD COLUMN expire TEXT")
 except:pass
 conn.commit()
 conn.close()
init_db()

def gen_code():
 return ''.join(random.choices(string.ascii_uppercase+string.digits,k=5))

def get_bg_style():
 for f in ["bg.jpg","bg.jpeg","bg.png","bg.JPG"]:
  if os.path.exists(f"static/{f}"):
   return f"background-image: url('/static/{f}'); background-size: cover; background-position: center; background-attachment: fixed;"
 return "background:#f0fdf4;"
STYLE_BG=get_bg_style()
LOGO_HTML="<img src='/static/logo.png' style='height:60px;width:60px;border-radius:50%;object-fit:cover;border:3px solid #16a34a;margin-right:15px;background:white' onerror=\"this.style.display='none'\">"

def clean_expired_auto():
 try:
  conn=sqlite3.connect(DB_PATH)
  now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  conn.execute("DELETE FROM tickets WHERE expire IS NOT NULL AND expire <?",(now,))
  conn.commit()
  conn.close()
 except:
  pass

@app.get("/verify")
def verify(code:str):
 conn=sqlite3.connect(DB_PATH)
 t=conn.execute("SELECT code,plan,prix,nom,created,first_use,expire FROM tickets WHERE code=?",(code.strip().upper(),)).fetchone()
 if not t:
  conn.close()
  return JSONResponse({"valid":False,"message":"Ticket INVALIDE"})
 code,plan,prix,nom,created,first_use,expire = t
 p=PLANS.get(plan)
 if not p:
  conn.close()
  return JSONResponse({"valid":False,"message":"Plan inconnu"})
 now=datetime.datetime.now()
 if first_use is None or first_use=="":
  first_dt=now
  expire_dt=now+datetime.timedelta(hours=p["hours"])
  conn.execute("UPDATE tickets SET first_use=?, expire=? WHERE code=?",(first_dt.strftime("%Y-%m-%d %H:%M:%S"),expire_dt.strftime("%Y-%m-%d %H:%M:%S"),code))
  conn.commit()
  conn.close()
  send_all(f"✅ Ticket {code} ACTIVÉ - {p['nom']} - expire le {expire_dt.strftime('%d/%m/%Y %H:%M')}",f"Ticket {code} ACTIVE - {p['nom']}")
  return JSONResponse({"valid":True,"message":f"Ticket ACTIVÉ! {p['nom']} - Valide jusqu'à {expire_dt.strftime('%d/%m/%Y %H:%M')}"})
 else:
  try:
   expire_dt=datetime.datetime.strptime(expire,"%Y-%m-%d %H:%M:%S")
  except:
   conn.close()
   return JSONResponse({"valid":False,"message":"Ticket ERREUR date"})
  if now > expire_dt:
   conn.execute("DELETE FROM tickets WHERE code=?",(code,))
   conn.commit()
   conn.close()
   send_all(f"❌ Ticket {code} EXPIRÉ tenté",f"Ticket {code} EXPIRE")
   return JSONResponse({"valid":False,"message":"Ticket EXPIRÉ"})
  else:
   reste=expire_dt-now
   heures=int(reste.total_seconds()//3600)
   minutes=int((reste.total_seconds()%3600)//60)
   conn.close()
   return JSONResponse({"valid":True,"message":f"Ticket VALIDE - Reste {heures}h {minutes}min - Expire {expire_dt.strftime('%d/%m %H:%M')}"})

@app.get("/admin")
def admin(pwd=""):
 if pwd!=PWD:
  return HTMLResponse("Mot de passe faux",401)
 clean_expired_auto()
 conn=sqlite3.connect(DB_PATH)
 tickets=conn.execute("SELECT code,plan,prix,nom,created,first_use,expire FROM tickets ORDER BY created DESC LIMIT 200").fetchall()
 total=conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
 non_util=conn.execute("SELECT COUNT(*) FROM tickets WHERE first_use IS NULL OR first_use=''").fetchone()[0]
 actifs=conn.execute("SELECT COUNT(*) FROM tickets WHERE first_use IS NOT NULL AND first_use!='' AND (expire IS NULL OR expire >?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)).fetchone()[0]
 conn.close()
 date=datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
 rows=""
 for i,(key,p) in enumerate(PLANS.items(),1):
  bg="#fef3c7" if p["prix"]==0 else "white"
  btn="#f59e0b" if p["prix"]==0 else "#16a34a"
  q=10 if p["prix"]==0 else 40
  rows+=f"<tr style='background:{bg};border-bottom:1px solid #eee'><td style='padding:12px'>{i}</td><td style='padding:12px'><b>{p['nom']}</b><br><small>{p['hours']}h après 1ère co</small></td><td style='padding:12px'>{p['duree_str']}</td><td style='padding:12px'><b>{p['prix']} F</b></td><td style='padding:12px'><input id='q-{key}' value='{q}' style='width:50px;padding:5px'></td><td style='padding:12px'><button onclick='generer(\"{key}\")' style='background:{btn};color:white;border:none;padding:8px 10px;border-radius:5px;cursor:pointer'>GEN</button> <button onclick='supprimerPlan(\"{key}\")' style='background:#dc2626;color:white;border:none;padding:8px 10px;border-radius:5px;cursor:pointer'>SUPPR LOT</button></td></tr>"
 th=""
 for t in tickets:
  code,plan,prix,nom,created,first_use,expire = t[0],t[1],t[2],t[3],t[4],t[5],t[6] if len(t)>6 else None
  if not first_use:
   statut="<span style='background:#e5e7eb;padding:3px 8px;border-radius:10px;color:#374151'>NON UTILISÉ</span>"
   exp_aff="Attend 1ère co"
  else:
   try:
    exp_dt=datetime.datetime.strptime(expire,"%Y-%m-%d %H:%M:%S")
    if exp_dt < datetime.datetime.now():
     statut="<span style='background:#fee2e2;padding:3px 8px;border-radius:10px;color:#dc2626'>EXPIRÉ</span>"
    else:
     statut="<span style='background:#dcfce7;padding:3px 8px;border-radius:10px;color:#16a34a'>ACTIF</span>"
    exp_aff=expire[:16]
   except:
    statut="<span style='background:#e5e7eb;padding:3px 8px;border-radius:10px'>?</span>"
    exp_aff=expire or "-"
  th+=f"<tr style='border-bottom:1px solid #eee'><td style='padding:8px'><input type='checkbox' class='chk' value='{code}'></td><td style='padding:8px;font-family:monospace;font-weight:bold'>{code}</td><td style='padding:8px'>{nom}</td><td style='padding:8px'>{prix}F</td><td style='padding:8px'>{statut}</td><td style='padding:8px'><small>1ère co: {first_use or '-'}<br>Expire: {exp_aff}</small></td><td style='padding:8px'><button onclick='supprimer(\"{code}\")' style='background:#dc2626;color:white;border:none;padding:5px 8px;border-radius:4px;cursor:pointer'>X</button></td></tr>"
 if not th:
  th="<tr><td colspan=7 style='padding:20px;text-align:center;color:#999'>Aucun ticket</td></tr>"
 html=f"<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>FAROUK-TCS</title></head><body style='font-family:Arial;margin:0;padding:20px;{STYLE_BG}'><div style='max-width:1250px;margin:auto'><div style='display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.95);padding:15px 20px;border-radius:12px;'><div style='display:flex;align-items:center'>{LOGO_HTML}<div><h1 style='margin:0;color:#16a34a;font-size:18px'>FAROUK-TCS ZINDER</h1><small>{date} | Total:{total} | Non utilisés:{non_util} | Actifs:{actifs}</small></div></div><div style='display:flex;gap:8px;flex-wrap:wrap'><a href='/clean?pwd={PWD}' style='background:#f97316;color:white;padding:10px;border-radius:8px;text-decoration:none'>NETTOYER EXPIRÉS</a><a href='/print?pwd={PWD}' style='background:#2563eb;color:white;padding:10px;border-radius:8px;text-decoration:none'>RAPPORT</a><a href='/logout' style='background:#dc2626;color:white;padding:10px;border-radius:8px;text-decoration:none'>EXIT</a></div></div><div style='background:#fef9c3;padding:15px;border-radius:12px;margin-top:20px;border:2px solid #facc15'><b>🔗 Lien de vérification client:</b><br><code style='font-size:14px'>/verify?code=CODE_TICKET</code><br><small>Le client entre son code 5 caractères ici → ça active le chrono!</small></div><div style='background:rgba(255,255,255,0.92);padding:20px;border-radius:12px;margin-top:20px'><h3>8 Forfaits - Expiration à la 1ère connexion</h3><table style='width:100%;border-collapse:collapse'><tr style='background:#dcfce7'><th style='padding:12px;text-align:left'>N°</th><th>FORFAIT</th><th>DUREE</th><th>PRIX</th><th>QTE</th><th>ACTION</th></tr>{rows}</table><br><button onclick='genererAll()' style='background:#ea580c;color:white;border:none;padding:12px 20px;border-radius:8px;font-weight:bold'>GENERER 4000 TICKETS (5 car.)</button></div><div style='background:rgba(255,255,255,0.92);padding:20px;border-radius:12px;margin-top:20px'><div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px'><h3>Tickets ({total})</h3><div style='display:flex;gap:8px'><button onclick='checkAll(true)' style='background:#6b7280;color:white;padding:8px 12px;border:none;border-radius:5px'>TOUT COCHER</button><button onclick='checkAll(false)' style='background:#9ca3af;color:white;padding:8px 12px;border:none;border-radius:5px'>DECOCHER</button><button onclick='supprimerSelection()' style='background:#dc2626;color:white;padding:8px 15px;border:none;border-radius:5px;font-weight:bold'>SUPPRIMER SELECTION</button><button onclick='supprimerAll()' style='background:#000;color:white;padding:8px 15px;border:none;border-radius:5px;font-weight:bold'>TOUT SUPPRIMER</button></div></div><table style='width:100%;margin-top:15px'><tr style='background:#f3f4f6'><th><input type='checkbox' id='master' onclick='checkAll(this.checked)'></th><th>CODE 5C</th><th>NOM</th><th>PRIX</th><th>STATUT</th><th>1ERE CO / EXPIRE</th><th>SUPPR</th></tr>{th}</table></div></div><script>function generer(p){{let q=document.getElementById('q-'+p).value;fetch('/generate?pwd={PWD}&plan='+p+'&qte='+q).then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}function genererAll(){{if(confirm('Generer 4000 tickets 5 caracteres?'))fetch('/generate_all?pwd={PWD}&qte=500').then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}function supprimer(code){{if(confirm('Supprimer '+code+'?'))fetch('/delete?pwd={PWD}&code='+code).then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}function supprimerPlan(plan){{let q=prompt('Combien de tickets '+plan+' supprimer? (0 = tous)','10'); if(q!==null){{fetch('/delete_plan?pwd={PWD}&plan='+plan+'&qte='+q).then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}}}function checkAll(v){{document.querySelectorAll('.chk').forEach(c=>c.checked=v); document.getElementById('master').checked=v;}}function supprimerSelection(){{let codes=[...document.querySelectorAll('.chk:checked')].map(c=>c.value); if(codes.length==0){{alert('Coche au moins 1 ticket');return;}} if(confirm('Supprimer '+codes.length+' tickets?')){{fetch('/delete_bulk?pwd={PWD}&codes='+codes.join(',')).then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}}}function supprimerAll(){{if(confirm('SUPPRIMER TOUS LES '+{total}+' TICKETS?')){{if(confirm('Vraiment tout?')){{fetch('/delete_all?pwd={PWD}').then(r=>r.json()).then(d=>{{alert(d.message);location.reload()}})}}}}}}</script></body></html>"
 return HTMLResponse(html)

@app.get("/generate")
def generate(pwd,plan,qte:int=40):
 if pwd!=PWD:
  return JSONResponse({"message":"pwd faux"})
 conn=sqlite3.connect(DB_PATH)
 p=PLANS[plan]
 c=0
 now=datetime.datetime.now()
 for _ in range(qte):
  code=gen_code()
  try:
   conn.execute("INSERT INTO tickets (code,plan,prix,nom,created,first_use,expire) VALUES (?,?,?,?,?,?,?)",(code,plan,p["prix"],p["nom"],now.strftime("%Y-%m-%d %H:%M:%S"),None,None))
   c+=1
  except:
   pass
 conn.commit()
 conn.close()
 send_all(f"VENTE {p['nom']} {p['prix']}F x{c} (5 car) - Actif à 1ère co",f"VENTE {p['nom']} {p['prix']}F x{c}")
 return {"message":f"{c} tickets {p['nom']} 5 CAR. generes! Expire {p['hours']}h après 1ère connexion"}

@app.get("/generate_all")
def generate_all(pwd,qte:int=500):
 conn=sqlite3.connect(DB_PATH)
 t=0
 now=datetime.datetime.now()
 for k,p in PLANS.items():
  for _ in range(qte):
   try:
    conn.execute("INSERT INTO tickets (code,plan,prix,nom,created,first_use,expire) VALUES (?,?,?,?,?,?,?)",(gen_code(),k,p["prix"],p["nom"],now.strftime("%Y-%m-%d %H:%M:%S"),None,None))
    t+=1
   except:
    pass
 conn.commit()
 conn.close()
 send_all(f"{t} tickets 5 CAR. generes",f"{t} tickets 5 CAR. generes FAROUK-TCS")
 return {"message":f"{t} tickets 5 caracteres generes!"}

@app.get("/delete")
def delete_ticket(pwd,code:str):
 if pwd!=PWD:
  return JSONResponse({"message":"pwd faux"})
 conn=sqlite3.connect(DB_PATH)
 conn.execute("DELETE FROM tickets WHERE code=?",(code,))
 conn.commit()
 conn.close()
 return {"message":f"Ticket {code} supprime!"}

@app.get("/delete_plan")
def delete_plan(pwd,plan,qte:int=0):
 if pwd!=PWD:
  return JSONResponse({"message":"pwd faux"})
 conn=sqlite3.connect(DB_PATH)
 if qte==0:
  cur=conn.execute("DELETE FROM tickets WHERE plan=?",(plan,))
  n=cur.rowcount
 else:
  cur=conn.execute(f"DELETE FROM tickets WHERE code IN (SELECT code FROM tickets WHERE plan=? LIMIT {qte})",(plan,))
  n=cur.rowcount
 conn.commit()
 conn.close()
 return {"message":f"{n} tickets {plan} supprimes!"}

@app.get("/delete_bulk")
def delete_bulk(pwd,codes:str):
 if pwd!=PWD:
  return JSONResponse({"message":"pwd faux"})
 liste=codes.split(",")
 conn=sqlite3.connect(DB_PATH)
 n=0
 for c in liste:
  cur=conn.execute("DELETE FROM tickets WHERE code=?",(c.strip(),))
  n+=cur.rowcount
 conn.commit()
 conn.close()
 return {"message":f"{n} tickets supprimes par lot!"}

@app.get("/delete_all")
def delete_all(pwd):
 if pwd!=PWD:
  return JSONResponse({"message":"pwd faux"})
 conn=sqlite3.connect(DB_PATH)
 cur=conn.execute("DELETE FROM tickets")
 n=cur.rowcount
 conn.commit()
 conn.close()
 return {"message":f"Tous les {n} tickets supprimes!"}

@app.get("/clean")
def clean_expired(pwd):
 if pwd!=PWD:
  return HTMLResponse("pwd faux",401)
 conn=sqlite3.connect(DB_PATH)
 now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 cur=conn.execute("DELETE FROM tickets WHERE expire IS NOT NULL AND expire <?", (now,))
 n=cur.rowcount
 conn.commit()
 conn.close()
 return RedirectResponse(f"/admin?pwd={PWD}",302)

@app.get("/logout")
def logout():
 return RedirectResponse("/",302)

@app.get("/print")
def print_page(pwd):
 if pwd!=PWD:
  return HTMLResponse("pwd faux",401)
 conn=sqlite3.connect(DB_PATH)
 tickets=conn.execute("SELECT code,plan,prix,nom,created,first_use,expire FROM tickets ORDER BY created DESC").fetchall()
 total=len(tickets)
 conn.close()
 h=""
 for x in tickets[:400]:
  h+=f"<div style='border:1px dashed #333;padding:8px;margin:5px;width:180px;display:inline-block;text-align:center;background:white'><b>FAROUK-TCS</b><br>{x[3]}<br><b style='font-size:20px;letter-spacing:2px'>{x[0]}</b><br>{x[2]}F<br><small>Active à 1ère co</small></div>"
 return HTMLResponse(f"<html><head><meta charset='utf-8'><style>body{{{STYLE_BG}}}</style></head><body style='font-family:Arial;padding:20px'><div style='background:white;padding:15px'><h2>RAPPORT {total} TICKETS 5 CAR - Expiration à 1ère connexion</h2></div><div style='background:white;padding:15px;margin-top:10px'>{h if h else 'Aucun'}</div><center><button onclick='window.print()' style='background:#16a34a;color:white;padding:15px 30px;border:none;border-radius:8px;margin-top:20px'>IMPRIMER</button></center></body></html>")

@app.get("/")
def home():
 return RedirectResponse(f"/admin?pwd={PWD}")

import os
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))