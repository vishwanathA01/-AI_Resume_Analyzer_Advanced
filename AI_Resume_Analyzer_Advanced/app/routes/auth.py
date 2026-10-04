from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


def _valid_email(email):
    if len(email) > 180 or any(character.isspace() for character in email):
        return False
    local, separator, domain = email.rpartition("@")
    if not separator or not local or not domain or len(local) > 64:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    labels = domain.split(".")
    return len(labels) > 1 and all(
        label
        and len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in label)
        for label in labels
    )


@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 120 or not _valid_email(email) or not password:
            flash("Enter a name and valid email address, then complete every field.")
            return render_template("register.html"), 400
        if len(password) < 8 or len(password) > 128:
            flash("Your password must be between 8 and 128 characters.")
            return render_template("register.html"), 400
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if User.query.filter_by(email=email).first():
                flash("Email already registered.")
                return render_template("register.html"), 409
            raise
        flash("Account created. Please login.")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Enter your email and password.")
            return render_template("login.html"), 400
        if len(password) > 128 or not _valid_email(email):
            flash("Invalid email or password.")
            return render_template("login.html")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            destination = "admin.dashboard" if user.role == "admin" else "main.dashboard"
            return redirect(url_for(destination))
        flash("Invalid email or password.")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
