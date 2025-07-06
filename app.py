from cs50 import SQL
from flask import Flask, redirect, render_template, request, url_for, session, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from flask_mail import Mail, Message
import random, time

import os
from werkzeug.utils import secure_filename

import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "instance", "app.db")
sqlite3.connect(db_path).close()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db = SQL(f"sqlite:///{db_path}")


db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        user_name TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS blogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        image_url TEXT,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        blog_id INTEGER NOT NULL,
        UNIQUE(user_id, blog_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (blog_id) REFERENCES blogs(id)
    );
""")


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    recent_blogs = db.execute("""
        SELECT id, title, content, created_at, category, image_url FROM blogs ORDER BY created_at DESC LIMIT 3
    """)

    return render_template("index.html", active_page="index", recent_blogs=recent_blogs)

@app.route("/blog/<int:blog_id>")
def view_blog(blog_id):
    user_id = session.get("user_id")

    blog = db.execute("""
        SELECT blogs.*, users.user_name
        FROM blogs
        JOIN users ON blogs.user_id = users.id
        WHERE blogs.id = ?
    """, blog_id)

    if not blog:
        flash("Blog not found!")
        return redirect("/")

    blog = blog[0]

    like_data = db.execute("SELECT COUNT(*) AS count FROM likes WHERE blog_id = ?", blog_id)
    blog['like_count'] = like_data[0]['count'] if like_data else 0

    blog['has_liked'] = False
    if user_id:
        liked = db.execute("SELECT 1 FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog_id)
        blog['has_liked'] = bool(liked)

    return render_template("view_blog.html", blog=blog)



@app.route("/user/<user_name>")
def user_blogs(user_name):
    user = db.execute("SELECT id FROM users WHERE user_name = ?", user_name)
    if not user:
        flash("User not found.")
        return redirect("/")

    blogs = db.execute("SELECT * FROM blogs WHERE user_id = ? ORDER BY created_at DESC", user[0]["id"])
    return render_template("user_blogs.html", user_name=user_name, blogs=blogs)

@app.route("/toggle_like/<int:blog_id>", methods=["POST"])
def toggle_like_ajax(blog_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Login required"}), 401

    liked = db.execute("SELECT id FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog_id)

    if liked:
        db.execute("DELETE FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog_id)
        action = "unliked"
    else:
        db.execute("INSERT INTO likes (user_id, blog_id) VALUES (?, ?)", user_id, blog_id)
        action = "liked"

    like_count = db.execute("SELECT COUNT(*) AS count FROM likes WHERE blog_id = ?", blog_id)[0]["count"]
    return jsonify({"success": True, "action": action, "like_count": like_count})


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["reg_name"]
        user_name = request.form["reg_username"]
        email = request.form["reg_email"]
        password = request.form["reg_password"]
        confirm_password = request.form["reg_confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for("signup"))

        if db.execute("SELECT * FROM users WHERE user_name = ?", user_name):
            flash("Username already taken!")
            return redirect(url_for("signup"))

        if db.execute("SELECT * FROM users WHERE email = ?", email):
            flash("Email already registered!")
            return redirect(url_for("signup"))
        
        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (name, user_name, email, password) VALUES (?, ?, ?, ?)",
            name, user_name, email, hashed_password
        )

        flash("Signup successful! You can now log in.")
        

    return render_template("signup.html", active_page="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        identifier = request.form["identifier"]
        password = request.form["password"]     

        user = db.execute("SELECT * FROM users WHERE email = ? or user_name = ?", identifier, identifier)   
        if not user:
            flash("User not found! Please sign up.")
            return redirect(url_for("login"))
        
        if not check_password_hash(user[0]['password'], password):
            flash("Incorrect password!")
            return redirect(url_for("login"))
        
        session["user_id"] = user[0]['id']
        session["name"] = user[0]['name']
        session["user_name"] = user[0]['user_name']
        flash("Logged in Successfully!") 
        return redirect(url_for('index'))
    
    return render_template("login.html", active_page="login")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = db.execute("SELECT * FROM users WHERE email = ?", email)
        if user:
            session["reset_email"] = email
            flash("Email verified. You can now reset your password.")
            return redirect("/reset_password")
        else:
            flash("Email not found.")
            return redirect("/forgot_password")

    return render_template("forgot_password.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    if not email:
        flash("Session expired. Try again.")
        return redirect("/forgot_password")

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect("/reset_password")

        hashed = generate_password_hash(new_password)
        db.execute("UPDATE users SET password = ? WHERE email = ?", hashed, email)
        session.pop("reset_email", None)
        flash("Password reset successful. Please log in.")
        return redirect("/login")

    return render_template("reset_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your profile.")
        return redirect(url_for("login"))

    user = db.execute("SELECT name, user_name, email FROM users WHERE id = ?", user_id)[0]

    blog_count = db.execute("SELECT COUNT(*) AS count FROM blogs WHERE user_id = ?", user_id)[0]['count']
    liked_count = db.execute("SELECT COUNT(*) AS count FROM likes WHERE user_id = ?", user_id)[0]['count']

    return render_template("profile.html", user=user, blog_count=blog_count, liked_count=liked_count, active_page="profile")

@app.route("/liked_blogs") 
def liked_blogs():
    user_id  = session.get("user_id")
    if not user_id:
        flash("Please log in to view liked blogs.")
        return redirect(url_for("login"))

    liked = db.execute("""
        SELECT blogs.*, users.user_name
        FROM likes
        JOIN blogs ON likes.blog_id = blogs.id
        JOIN users ON blogs.user_id = users.id
        WHERE likes.user_id = ?
        ORDER BY blogs.created_at DESC
    """, user_id)   

    return render_template("liked_blogs.html", blogs=liked, active_page="liked_blogs")

@app.route("/top_blogs")
def top_blogs():
    user_id = session.get("user_id")

    top_blogs = db.execute("""
        SELECT blogs.*, users.user_name, COUNT(likes.id) AS like_count
        FROM blogs
        LEFT JOIN likes ON blogs.id = likes.blog_id
        JOIN users ON blogs.user_id = users.id
        GROUP BY blogs.id
        ORDER BY like_count DESC, created_at DESC
        LIMIT 10;
    """)

    for blog in top_blogs:
        if user_id:
            liked = db.execute("SELECT 1 FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog["id"])
            blog["has_liked"] = bool(liked)
        else:
            blog["has_liked"] = False

    return render_template("top_blogs.html", active_page="top_blogs", blogs=top_blogs)

@app.route("/my_blogs")
def my_blogs():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your blogs.")
        return redirect("/login")

    user_blogs = db.execute(  
        "SELECT id, title, content, created_at, image_url, category FROM blogs WHERE user_id = ? ORDER BY created_at DESC",
        user_id
    )

    for blog in user_blogs:
        blog["has_liked"] = bool(db.execute("SELECT 1 FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog["id"]))
        blog["like_count"] = db.execute("SELECT COUNT(*) AS count FROM likes WHERE blog_id = ?", blog["id"])[0]["count"]

    return render_template("my_blogs.html", active_page="my_blogs", blogs=user_blogs)

@app.route("/edit_blog/<int:blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to edit blogs.")
        return redirect("/login")

    blog = db.execute("SELECT * FROM blogs WHERE id = ? AND user_id = ?", blog_id, user_id)
    if not blog:
        flash("Blog not found or access denied.")
        return redirect("/my_blogs")

    blog = blog[0]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not content or not category:
            flash("All fields are required.")
            return redirect(request.url)

        db.execute(
            "UPDATE blogs SET title = ?, content = ?, category = ? WHERE id = ? AND user_id = ?",
            title, content, category, blog_id, user_id
        )

        flash("Blog updated successfully!")
        return redirect("/my_blogs")

    return render_template("edit_blog.html", blog=blog)


@app.route("/delete_blog/<int:blog_id>", methods=["POST"])
def delete_blog(blog_id):
    user_id = session.get("user_id")

    db.execute("DELETE FROM likes WHERE blog_id = ?", blog_id)
    db.execute("DELETE FROM blogs WHERE id = ? AND user_id = ?", blog_id, user_id)

    flash("Blog deleted successfully.")
    return redirect("/my_blogs")



@app.route("/create_blog", methods=["GET", "POST"])
def create_blog():
    
    user_id = session.get("user_id")
    if not user_id:
        flash("User not found! Please log in.")
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]

        if not title or not content:
            flash("Title and content are required!")
            return redirect("/create_blog")
        
        if not category:
            flash("Category is required!")
            return redirect("/create_blog")
    
        image_url = None
        if "image" in request.files:
            image = request.files["image"]
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

                image.save(save_path)
                image_url = f"/static/images/{filename}"

        db.execute(
            "INSERT INTO blogs (user_id, title, content, image_url, category) VALUES (?, ?, ?, ?, ?)",
            user_id, title, content, image_url, category
        )
        
        flash("Blog created successfully!")
        return redirect("/create_blog")

    return render_template("create_blog.html", active_page="create_blog")

@app.route("/category/<category_name>")
def category(category_name):

    blogs = db.execute("""
        SELECT blogs.*, users.user_name
        FROM blogs
        JOIN users ON blogs.user_id = users.id
        WHERE category = ?
        ORDER BY created_at DESC               
    """,category_name)

    user_id = session.get("user_id")
    for blog in blogs:
        blog["like_count"] = db.execute("SELECT COUNT(*) as count FROM likes WHERE blog_id = ?", blog["id"])[0]["count"]
        blog["has_liked"] = bool(db.execute("SELECT 1 FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog["id"])) if user_id else False

    return render_template("category_blogs.html", blogs=blogs, category=category_name, active_page=None)


if __name__ == "__main__":
    app.run(debug=True)