from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date, timedelta
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "локальный-ключ-для-разработки")
DB = "expenses.db"


# ---------- БАЗА ДАННЫХ ----------
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


# ---------- ПОЛЬЗОВАТЕЛИ ----------
def get_user_by_name(username):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def create_user(username, password):
    password_hash = generate_password_hash(password)
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    conn.commit()
    conn.close()


# ---------- РАСХОДЫ ----------
def add_expense(user_id, amount, category, date_val, comment):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, date, comment) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_val, comment)
    )
    conn.commit()
    conn.close()


def get_expenses(user_id, period=None):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if period == "today":
        start = date.today().isoformat()
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = ? AND date = ? ORDER BY date DESC",
            (user_id, start)
        )
    elif period == "week":
        start = (date.today() - timedelta(days=7)).isoformat()
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = ? AND date >= ? ORDER BY date DESC",
            (user_id, start)
        )
    elif period == "month":
        start = (date.today() - timedelta(days=30)).isoformat()
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = ? AND date >= ? ORDER BY date DESC",
            (user_id, start)
        )
    else:
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        )

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_total(user_id, period=None):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if period == "today":
        start = date.today().isoformat()
        cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date = ?",
            (user_id, start)
        )
    elif period == "week":
        start = (date.today() - timedelta(days=7)).isoformat()
        cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date >= ?",
            (user_id, start)
        )
    elif period == "month":
        start = (date.today() - timedelta(days=30)).isoformat()
        cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date >= ?",
            (user_id, start)
        )
    else:
        cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id = ?",
            (user_id,)
        )

    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0


def delete_expense(expense_id, user_id):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    conn.commit()
    conn.close()


# ---------- ГРАФИК ----------
def build_chart(user_id):
    os.makedirs("static", exist_ok=True)

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category",
        (user_id,)
    )
    data = cursor.fetchall()
    conn.close()

    if not data:
        return

    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    plt.figure(figsize=(6, 5))
    plt.pie(amounts, labels=categories, autopct="%1.1f%%",
            labeldistance=1.15, pctdistance=0.75)
    plt.title("Расходы по категориям")
    plt.subplots_adjust(left=0.05, right=0.75, top=0.9, bottom=0.1)
    plt.savefig("static/chart.png", bbox_inches="tight")
    plt.close()


# ---------- ПРОВЕРКА АВТОРИЗАЦИИ ----------
def is_logged_in():
    return "user_id" in session


# ---------- МАРШРУТЫ ----------
@app.route("/add", methods=["POST"])
def add():
    if not is_logged_in():
        return redirect("/login")

    amount = request.form.get("amount")
    category = request.form.get("category")
    date_val = request.form.get("date")
    comment = request.form.get("comment", "")

    if amount and category and date_val:
        add_expense(session["user_id"], amount, category, date_val, comment)

    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            return render_template("register.html", error="Заполни все поля")

        if password != password2:
            return render_template("register.html", error="Пароли не совпадают")

        if len(password) < 6:
            return render_template("register.html", error="Пароль минимум 6 символов")

        if get_user_by_name(username):
            return render_template("register.html", error="Такое имя уже занято")

        create_user(username, password)
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_name(username)

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/")
        else:
            return render_template("login.html", error="Неверное имя или пароль")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/", methods=["GET", "POST"])
def index():
    if not is_logged_in():
        return redirect("/login")

    period = request.args.get("period")

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        date_val = request.form.get("date")
        comment = request.form.get("comment", "")

        if amount and category and date_val:
            add_expense(session["user_id"], amount, category, date_val, comment)

        return redirect("/")

    expenses = get_expenses(session["user_id"], period)
    total = get_total(session["user_id"], period)
    build_chart(session["user_id"])

    return render_template(
        "index.html",
        expenses=expenses,
        period=period,
        total=total,
        username=session["username"]
    )


@app.route("/delete/<int:expense_id>")
def delete(expense_id):
    if not is_logged_in():
        return redirect("/login")

    delete_expense(expense_id, session["user_id"])
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)