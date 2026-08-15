import os
from dotenv import load_dotenv
from cs50 import SQL
from flask import Flask, redirect, render_template, request, url_for, session, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
import random, time
import uuid
import bleach
from werkzeug.utils import secure_filename
import sqlite3

# Load environment variables first
load_dotenv()

db_path = os.path.join(os.path.dirname(__file__), "instance", "app.db")
sqlite3.connect(db_path).close()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_dev_key")

db = SQL(f"sqlite:///{db_path}")

# --- DATABASE SETUP ---
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

# --- MAIL CONFIGURATION ---
# Using Gmail SMTP.
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Initialize the token serializer for password resets
s = URLSafeTimedSerializer(app.secret_key)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# --- UPLOAD CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- BLEACH CONFIGURATION (XSS PROTECTION) ---
# Only allowing these specific HTML tags from the Quill editor
ALLOWED_TAGS = [
    'p', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3', 
    'ol', 'ul', 'li', 'a', 'br'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target']
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route("/")
def index():
    recent_blogs = db.execute("""
        SELECT id, title, content, created_at, category, image_url 
        FROM blogs 
        ORDER BY created_at DESC LIMIT 3
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
        flash("Blog not found!", "danger")
        return redirect("/")

    blog = blog[0]

    # Fetching total likes for this specific blog
    like_data = db.execute("SELECT COUNT(*) AS count FROM likes WHERE blog_id = ?", blog_id)
    blog['like_count'] = like_data[0]['count'] if like_data else 0

    # Checking if the current user liked it
    blog['has_liked'] = False
    if user_id:
        liked = db.execute("SELECT 1 FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog_id)
        blog['has_liked'] = bool(liked)

    return render_template("view_blog.html", blog=blog)


@app.route("/user/<user_name>")
def user_blogs(user_name):
    user = db.execute("SELECT id FROM users WHERE user_name = ?", user_name)
    if not user:
        flash("User not found.", "danger")
        return redirect("/")

    blogs = db.execute("SELECT * FROM blogs WHERE user_id = ? ORDER BY created_at DESC", user[0]["id"])
    return render_template("user_blogs.html", user_name=user_name, blogs=blogs)


@app.route("/toggle_like/<int:blog_id>", methods=["POST"])
def toggle_like_ajax(blog_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Login required"}), 401

    liked = db.execute("SELECT id FROM likes WHERE user_id = ? AND blog_id = ?", user_id, blog_id)

    # Toggle logic: if it exists, delete it. If not, insert it.
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
            flash("Passwords do not match!", "danger")
            return redirect(url_for("signup"))

        if db.execute("SELECT * FROM users WHERE user_name = ?", user_name):
            flash("Username already taken!", "danger")
            return redirect(url_for("signup"))

        if db.execute("SELECT * FROM users WHERE email = ?", email):
            flash("Email already registered!", "danger")
            return redirect(url_for("signup"))
        
        # Hashing the password so it's not stored in plain text
        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (name, user_name, email, password) VALUES (?, ?, ?, ?)",
            name, user_name, email, hashed_password
        )

        flash("Signup successful! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", active_page="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        identifier = request.form["identifier"]
        password = request.form["password"]    

        # Allow login with either email or username
        user = db.execute("SELECT * FROM users WHERE email = ? or user_name = ?", identifier, identifier)   
        if not user:
            flash("User not found! Please sign up.", "danger")
            return redirect(url_for("login"))
        
        if not check_password_hash(user[0]['password'], password):
            flash("Incorrect password!", "danger")
            return redirect(url_for("login"))
        
        # Set up the session variables
        session["user_id"] = user[0]['id']
        session["name"] = user[0]['name']
        session["user_name"] = user[0]['user_name']
        
        flash("Logged in Successfully!", "success") 
        return redirect(url_for('index'))
    
    return render_template("login.html", active_page="login")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = db.execute("SELECT * FROM users WHERE email = ?", email)
        
        if user:
            # Generate a secure token tied to their email
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)

            msg = Message("Password Reset Request", recipients=[email])
            msg.body = f"Click this link to reset your password (valid for 15 minutes): {reset_link}"
            mail.send(msg)

        # SECURITY BEST PRACTICE: Always show this message even if the email doesn't exist to prevent enumeration
        flash("If that email exists in our system, a reset link has been sent.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        # Verify token. max_age=900 limits it to 15 minutes.
        email = s.loads(token, salt='password-reset-salt', max_age=900)
    except SignatureExpired:
        flash("The password reset link has expired. Please request a new one.", "danger")
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash("Invalid password reset link.", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(request.url) 

        hashed = generate_password_hash(new_password)
        db.execute("UPDATE users SET password = ? WHERE email = ?", hashed, email)
        
        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your profile.", "info")
        return redirect(url_for("login"))

    user = db.execute("SELECT name, user_name, email FROM users WHERE id = ?", user_id)[0]
    blog_count = db.execute("SELECT COUNT(*) AS count FROM blogs WHERE user_id = ?", user_id)[0]['count']
    liked_count = db.execute("SELECT COUNT(*) AS count FROM likes WHERE user_id = ?", user_id)[0]['count']

    return render_template("profile.html", user=user, blog_count=blog_count, liked_count=liked_count, active_page="profile")


@app.route("/liked_blogs") 
def liked_blogs():
    user_id  = session.get("user_id")
    if not user_id:
        flash("Please log in to view liked blogs.", "info")
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
    user_id = session.get("user_id") or 0

    # FIX: Eliminated the N+1 loop here by handling the has_liked check inside the SQL query!
    top_blogs = db.execute("""
        SELECT blogs.*, users.user_name, 
               COUNT(likes.id) AS like_count,
               MAX(CASE WHEN likes.user_id = ? THEN 1 ELSE 0 END) AS has_liked
        FROM blogs
        LEFT JOIN likes ON blogs.id = likes.blog_id
        JOIN users ON blogs.user_id = users.id
        GROUP BY blogs.id
        ORDER BY like_count DESC, created_at DESC
        LIMIT 10;
    """, user_id)

    # Cast to boolean for the Jinja template
    for blog in top_blogs:
        blog["has_liked"] = bool(blog["has_liked"])

    return render_template("top_blogs.html", active_page="top_blogs", blogs=top_blogs)


@app.route("/my_blogs")
def my_blogs():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your blogs.", "info")
        return redirect("/login")

    # A single query handles fetching, counting, and checking the boolean state
    user_blogs = db.execute("""
        SELECT blogs.id, blogs.title, blogs.content, blogs.created_at, blogs.image_url, blogs.category,
               COUNT(likes.id) AS like_count,
               MAX(CASE WHEN likes.user_id = ? THEN 1 ELSE 0 END) AS has_liked
        FROM blogs
        LEFT JOIN likes ON blogs.id = likes.blog_id
        WHERE blogs.user_id = ?
        GROUP BY blogs.id
        ORDER BY blogs.created_at DESC
    """, user_id, user_id)

    for blog in user_blogs:
        blog["has_liked"] = bool(blog["has_liked"])

    return render_template("my_blogs.html", active_page="my_blogs", blogs=user_blogs)


@app.route("/edit_blog/<int:blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to edit blogs.", "info")
        return redirect("/login")

    blog = db.execute("SELECT * FROM blogs WHERE id = ? AND user_id = ?", blog_id, user_id)
    if not blog:
        flash("Blog not found or access denied.", "danger")
        return redirect("/my_blogs")

    blog = blog[0]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        raw_content = request.form.get("content", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not raw_content or not category:
            flash("All fields are required.", "danger")
            return redirect(request.url)

        # FIX: Clean the HTML here as well to prevent XSS during edits!
        clean_content = bleach.clean(
            raw_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

        db.execute(
            "UPDATE blogs SET title = ?, content = ?, category = ? WHERE id = ? AND user_id = ?",
            title, clean_content, category, blog_id, user_id
        )

        flash("Blog updated successfully!", "success")
        return redirect("/my_blogs")

    return render_template("edit_blog.html", blog=blog)


@app.route("/delete_blog/<int:blog_id>", methods=["POST"])
def delete_blog(blog_id):
    user_id = session.get("user_id")

    # Have to delete likes first because of foreign key constraints
    db.execute("DELETE FROM likes WHERE blog_id = ?", blog_id)
    db.execute("DELETE FROM blogs WHERE id = ? AND user_id = ?", blog_id, user_id)

    flash("Blog deleted successfully.", "success")
    return redirect("/my_blogs")


@app.route("/create_blog", methods=["GET", "POST"])
def create_blog():
    user_id = session.get("user_id")
    if not user_id:
        flash("User not found! Please log in.", "danger")
        return redirect("/login")

    if request.method == "POST":
        title = request.form.get("title")
        raw_content = request.form.get("content")
        category = request.form.get("category")

        if not title or not raw_content:
            flash("Title and content are required!", "danger")
            return redirect("/create_blog")
        
        if not category:
            flash("Category is required!", "danger")
            return redirect("/create_blog")
    
        # Sanitize HTML using Bleach before hitting the database
        clean_content = bleach.clean(
            raw_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

        image_url = None
        if "image" in request.files:
            image = request.files["image"]
            if image and allowed_file(image.filename):
                original_filename = secure_filename(image.filename)
                extension = original_filename.rsplit('.', 1)[1].lower()
                
                # Using UUID so users don't overwrite each other's images
                unique_filename = f"{uuid.uuid4().hex}.{extension}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                image.save(save_path)
                image_url = f"/static/images/{unique_filename}"

        db.execute(
            "INSERT INTO blogs (user_id, title, content, image_url, category) VALUES (?, ?, ?, ?, ?)",
            user_id, title, clean_content, image_url, category
        )
        
        flash("Blog created successfully!", "success")
        return redirect("/create_blog")

    return render_template("create_blog.html", active_page="create_blog")


@app.route("/category/<category_name>")
def category(category_name):
    # Defaulting to 0 if guest so the MAX(CASE...) SQL logic still works
    user_id = session.get("user_id") or 0 

    blogs = db.execute("""
        SELECT blogs.*, users.user_name,
               COUNT(likes.id) AS like_count,
               MAX(CASE WHEN likes.user_id = ? THEN 1 ELSE 0 END) AS has_liked
        FROM blogs
        JOIN users ON blogs.user_id = users.id
        LEFT JOIN likes ON blogs.id = likes.blog_id
        WHERE blogs.category = ?
        GROUP BY blogs.id
        ORDER BY blogs.created_at DESC               
    """, user_id, category_name)

    for blog in blogs:
        blog["has_liked"] = bool(blog["has_liked"])

    return render_template("category_blogs.html", blogs=blogs, category=category_name, active_page=None)


if __name__ == "__main__":
    app.run(debug=True)