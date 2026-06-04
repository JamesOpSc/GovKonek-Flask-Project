# GovKonek Backend - Local Setup & Testing Guide 🚀

Welcome to the GovKonek Backend repository! We are building the foundation using **Python, Flask, and SQLite**. 

To avoid database conflicts and broken dependencies, **do not share virtual environments or database files**. Everyone must set up their own local environment by following this guide.

---

## 🛠️ Prerequisites
Before you begin, ensure you have the following installed:
1. **Python** (Latest version)
2. **Git** (Install from [git-scm.com/downloads](https://git-scm.com/downloads) using default settings)
3. **GitHub Desktop**
4. **VS Code**

---

## ⚙️ Step 1: Clone the Repository
1. Open **GitHub Desktop**.
2. Go to **File > Clone repository**.
3. Select this repository from your list or paste the URL.
4. Choose a dedicated folder on your computer to save it, then click **Clone**.
5. Open that folder in **VS Code**.

---

## 🐍 Step 2: Set Up Your Virtual Environment
*Do not skip this step! It isolates our project packages from the rest of your computer.*

1. In VS Code, open a new terminal (`Ctrl` + `` ` ``).
2. Create the virtual environment by running:
   ```
      python -m venv venv
   ```

3. Activate the environment:
   ```bash
   # Windows:
   venv\Scripts\activate

   # Mac/Linux:
   source venv/bin/activate
   ```
   *(Success check: You should see `(venv)` at the beginning of your terminal line).*

## 📦 Step 3: Install Dependencies

1. With your `(venv)` active, install Flask and our project dependencies:
   ```bash
   pip install Flask Flask-Login Werkzeug

## 🗄️ Step 4: Generate Your Local Database

1. We use a Python script to automatically generate the `govkonek.db` file with all necessary tables and sample data (posts, projects, services, documents, and forum topics).
   ```bash
   python init_db.py
   ```
2. You should see `Database and all tables created successfully!`, and `govkonek.db` will appear in your project folder. *(Note: This file is ignored by Git, so your testing data stays local).*

---

## 🚀 Step 5: Run the Server & Test
1. Start the Flask application:
   ```bash
   python app.py
   ```
2. `Ctrl + Click` the link in the terminal (usually `http://127.0.0.1:5000`) to open it in your browser.

---


## 📁 Project Structure
```
GovKonek-Flask-Project/
├── app.py              # Flask application factory with dependency injection
├── config.py           # Injectable Config class (ENCAPSULATION: @property)
├── exceptions.py       # Custom exception hierarchy (EXCEPTION HANDLING)
├── init_db.py          # Database initialization & seed data
├── models.py           # User, CitizenUser, PublisherUser (INHERITANCE + POLYMORPHISM)
├── repository.py       # Database layer with BaseRepository (ABSTRACTION)
├── routes.py           # Flask HTTP routes (thin controllers)
├── service.py          # Business logic layer (Auth, Post, Voice, Project services)
├── templates/          # HTML templates
└── static/             # CSS, JS, images
```