from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("auth.register"))
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please login.")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
