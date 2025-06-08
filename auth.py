# 로그인, 회원가입

from flask import Blueprint, request, session, render_template, redirect
import sqlite3

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def home():
    return render_template("login.html")

@auth_bp.route("/home")
def home_dashboard():
    if "userid" not in session:
        return redirect("/")
    
    user_id = session.get("userid")
    coins = 0

    conn = sqlite3.connect("emotion.db")
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE userid = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        coins = result[0]

    return render_template("main.html", coins=coins, userid=user_id)


@auth_bp.route("/signup")
def go_register():
    return render_template("signup.html")

@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        userid = request.form["userid"]
        password = request.form["password"]
        phone = request.form["phone"]
    except Exception as e:
        return f"❌ 폼에서 값 추출 실패: {e}"

    conn = sqlite3.connect("emotion.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (userid, password, phone, coins) VALUES (?, ?, ?, 3)",
                       (userid, password, phone))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("signup.html", signup_failed=True)
    except Exception as e:
        conn.close()
        return f"❌ DB 저장 중 오류 발생: {e}"

    conn.close()
    # 성공 시 → 로그인 화면으로 이동
    return render_template("login.html", signup_success=True)


@auth_bp.route("/login", methods=["POST"])
def login():
    phone = request.form["phone"]
    password = request.form["password"]

    conn = sqlite3.connect("emotion.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone=? AND password=?", (phone, password))

    user = cursor.fetchone()
    conn.close()

    if user:
        session["userid"] = user[2]  # 예: "taei123"
        return redirect("/home")  # ✅ redirect로 메인 페이지로 이동
    else:
        return render_template("login.html", login_failed=True)
