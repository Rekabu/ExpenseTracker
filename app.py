from flask import Flask, render_template, request, redirect
from datetime import date, timedelta
import sqlite3
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import os
os.makedirs("static", exist_ok=True)

app = Flask(__name__)
DB = "expenses.db"

app.secret_key ="e8817fbab1a73526dc94ef0568bb6973090af3bd7a9d5843b458d9a47e2049db"

def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            comment TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
def add_expense(user_id, amount, category, date, comment):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO expenses (user_id, amount, category, date, comment)
        VALUES(?, ?, ?, ?, ?)
    """, (user_id, amount, category, date, comment))
    
    conn.commit()
    conn.close()
    
def get_expenses(period=None):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if period == "today":
        start = date.today().isoformat()
        cursor.execute("SELECT * FROM expenses WHERE date = ? ORDER BY date DESC", (start,))
    elif period == "week":
        start = (date.today() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT * FROM expenses WHERE date >= ? ORDER BY date DESC", (start,))
    elif period == "month":
        start = (date.today() - timedelta(days=30)).isoformat()
        cursor.execute("SELECT * FROM expenses WHERE date >= ? ORDER BY date DESC", (start,))
    else:
        cursor.execute("SELECT * FROM expenses ORDER BY date DESC")

    rows = cursor.fetchall()
    conn.close()
    return rows
    
def delete_expense(expense_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""DELETE from expenses WHERE id=?""", (expense_id,))
    conn.commit()
    conn.close()
    
def build_chart():
    os.makedirs("static", exist_ok=True)
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
    data = cursor.fetchall()
    conn.close()

    if not data:
        return   # нечего рисовать

    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    plt.figure(figsize=(6, 5))
    plt.pie(amounts, labels=categories, autopct="%1.1f%%", 
        labeldistance=1.15, pctdistance=0.75)
    plt.title("Расходы по категориям")
    plt.subplots_adjust(left=0.05, right=0.75, top=0.9, bottom=0.1)
    plt.savefig("static/chart.png", bbox_inches="tight")
    plt.close()

def get_total(period=None):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if period == "today":
        start = date.today().isoformat()
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE date = ?", (start,))
    elif period == "week":
        start = (date.today() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE date >= ?", (start,))
    elif period == "month":
        start = (date.today() - timedelta(days=30)).isoformat()
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE date >= ?", (start,))
    else:
        cursor.execute("SELECT SUM(amount) FROM expenses")

    result = cursor.fetchone()[0]   # ← первое значение из строки
    conn.close()
    return result if result else 0   # ← если None — вернуть 0
    
@app.route("/")
def index():
    period = request.args.get("period")
    expenses = get_expenses(period)
    total = get_total(period)
    build_chart()
    return render_template("index.html", expenses=expenses, period=period, total=total)

@app.route("/add", methods = ["POST"])
def add():
    amount = request.form.get("amount")
    category = request.form.get("category")
    date = request.form.get("date")
    comment = request.form.get("comment")
    
    if amount and category and date:
        add_expense(1, amount, category, date, comment)
        
    return redirect('/')

@app.route("/delete/<int:expense_id>")
def delete(expense_id):  
    delete_expense(expense_id)
    return redirect ('/')
        
if __name__ == "__main__":
    init_db()
    app.run(debug = True)