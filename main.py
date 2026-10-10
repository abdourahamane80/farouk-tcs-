import sqlite3, os
import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="."), name="static")

DB = "/var/data/farouk.db" if os.path.exists("/var/data") else "farouk.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, description TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, name TEXT, phone TEXT, date TEXT)""")
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (name, price, description) VALUES ('Pack FAROUK', 5000, 'Acces complet')")
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    items = ""
    for p in products:
        items += f"<div><h3>{p['name']}</h3><p>{p['description']}</p><p><b>{p['price']} FCFA</b></p><form method='post' action='/order'><input type='hidden' name='product_id' value='{p['id']}'><input name='name' placeholder='Ton nom' required><input name='phone' placeholder='Ton numero' required><button>Commander</button></form></div>"
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>FAROUK-TCS</title></head><body><img src='/static/logo.png' width='120'><h1>FAROUK-TCS</h1>{items}<p><a href='/admin'>Admin</a></p></body></html>"
    return HTMLResponse(html)

@app.post("/order")
def order(product_id: int = Form(...), name: str = Form(...), phone: str = Form(...)):
    conn = get_db()
    conn.execute("INSERT INTO orders (product_id, name, phone, date) VALUES (?,?,?,?)", (product_id, name, phone, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.get("/api/products")
def api_products():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return JSONResponse([dict(p) for p in products])

@app.get("/admin", response_class=HTMLResponse)
def admin():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    rows = "".join([f"<tr><td>{o['id']}</td><td>{o['name']}</td><td>{o['phone']}</td><td>{o['date']}</td></tr>" for o in orders])
    return HTMLResponse(f"<h1>Commandes</h1><table border='1'><tr><th>ID</th><th>Nom</th><th>Tel</th><th>Date</th></tr>{rows}</table><p><a href='/'>Retour</a></p>")
