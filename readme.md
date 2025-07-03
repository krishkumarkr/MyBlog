# MyBlog

**URL of my video**:  
[https://www.youtube.com/watch?v=YTANdiiI6pg&ab_channel=KrishKumar](https://www.youtube.com/watch?v=YTANdiiI6pg&ab_channel=KrishKumar)

---

## Overview

**MyBlog** is a fully functional blogging platform built using **Flask**, **SQLite**, **HTML/CSS**, and **Bootstrap**. This web application allows users to register, log in, create and edit blog posts, categorize them, like/unlike posts, and view content based on categories or preferences. With an intuitive and clean user interface, the platform encourages content sharing and user engagement. Features like image attachments for blogs, secure password hashing, and session-based authentication ensure both aesthetics and security.

This project represents a well-rounded demonstration of full-stack web development and touches upon important software engineering concepts such as templating, MVC architecture, RESTful routing, database management, security, and user experience.

---

## Features

- **User Authentication**: Secure sign-up, login, logout, and password reset flow.
- **Blog Creation**: Users can write rich blog posts with image uploads and optional categories.
- **Like System**: Logged-in users can like or unlike blogs.
- **Categories**: Blogs can be filtered by user-defined categories.
- **Personal Dashboard**: Users can manage their created blogs.
- **Responsive Design**: Clean layout using Bootstrap and custom CSS for mobile-friendly experience.

---

## Project Structure

### 📁 `MyBlog/`

This is the main project directory containing the app code and resources.

---

### 🔹 `app.py`

This is the heart of the application. It initializes the Flask app, sets up routes, and connects to the SQLite database using `cs50.SQL`.

Main responsibilities include:
- Defining and executing the schema for three primary tables: `users`, `blogs`, and `likes`.
- Handling routing logic for all key user interactions like viewing, creating, editing, liking, or deleting blogs.
- Managing session storage and authentication using `flask_session`.

---

### 🔹 `templates/`

This directory contains all the Jinja2 HTML templates rendered by Flask.

Key files:
- `layout.html`: Base layout for all pages using Jinja templating.
- `index.html`: Home page displaying all blog posts.
- `login.html`, `logout.html`, `forgot_password.html`: Forms and pages for user auth flow.
- `create_blog.html`, `edit_blog.html`, `my_blogs.html`: Interfaces for blog creation and user dashboard.
- `liked_blogs.html`, `category_blogs.html`: Filtered views of content liked by the user or from a category.

Each template uses Bootstrap and custom CSS to maintain a cohesive look and feel.

---

### 🔹 `static/`

This folder stores static assets like stylesheets and images.

- `css/style.css`: Custom styles for form elements, navbar, blog cards, and responsive behavior.
- `images/`: Aesthetic images used in blog previews or decorative purposes.

---

### 🔹 `requirements.txt`

Contains the list of Python dependencies:
```bash
Flask
cs50
flask_session
flask_mail
werkzeug
```
These packages are required to run the application successfully and should be installed in a virtual environment.

---

### 🔹 `blogs_db.db`, `users.db`, `users_db.db`

These are SQLite databases. Only `app.db` (inside `instance/`) is actively used, while the rest appear to be test or backup databases created during development.

---

## Database Design

The database schema is simple yet powerful:

- **users**: Stores user credentials and metadata.
- **blogs**: Stores blog content, image URLs, and links to the user who wrote it.
- **likes**: Many-to-many relationship between users and blogs.

Each table is initialized inside `app.py` with schema safety checks (`CREATE TABLE IF NOT EXISTS`).

---

## Design Decisions

### ✅ Use of `cs50.SQL`
Instead of raw SQLite queries, I chose `cs50.SQL` for its simplicity and safety. It allows for clean and readable parameterized queries, which reduce the risk of SQL injection and make debugging easier.

### ✅ File Structure
Keeping everything inside one `app.py` makes the project manageable for smaller-scale applications. However, in a production-grade app, I would use a modular Flask blueprint approach and separate `models`, `routes`, and `forms`.

### ✅ Session Management
Flask’s server-side session storage (`flask_session`) was chosen to keep login state secure and avoid client-side manipulation.

### ✅ Image Uploading
Instead of directly embedding images into the database, this app stores image file paths, which is a more scalable and performant solution.

---

## Running the Project

1. **Clone the Repository**
   ```bash
   git clone <repo-url>
   cd MyBlog
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

3. **Run the App**
   ```bash
   python app.py
   ```

4. **Navigate to** `http://127.0.0.1:5000` in your browser.

---

## Potential Improvements

- Add search functionality across blogs.
- Implement email-based password reset.
- Refactor to use Blueprints for better scalability.
- Support comments on blogs.
- Paginate blog listing for performance with many entries.

---

## Conclusion

MyBlog is not just a blogging platform, but a hands-on exercise in full-stack development. Through building this, I have tackled challenges in database design, authentication, templating, and frontend design. I'm proud of what this project demonstrates, and I'm excited about how it could evolve into something even more powerful.
