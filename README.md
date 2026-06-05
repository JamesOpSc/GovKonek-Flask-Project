# GovKonek — Local Setup & Development Guide 🚀

Welcome to the GovKonek repository! We are building a **full-stack web application** using **Python, Flask, and SQLite** to connect citizens with their local barangay government.

To avoid database conflicts and broken dependencies, **do not share virtual environments or database files**. Everyone must set up their own local environment by following this guide.

---

## 🛠️ Prerequisites
Before you begin, ensure you have the following installed:
1. **Python** (Latest version recommended)
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
   pip install Flask Flask-Login Werkzeug requests pytest
   ```
   > **Note:** `requests` is required for the live weather API feature. `pytest` is needed for running the test suite.

## 🗄️ Step 4: Generate Your Local Database

1. We use a Python script to automatically generate the `govkonek.db` file with all necessary tables and sample data (posts, projects, services, documents, barangays, and forum topics).
   ```bash
   python init_db.py
   ```
2. You should see `Database and all tables created successfully!`, and `govkonek.db` will appear in your project folder. *(Note: This file is ignored by Git, so your testing data stays local).*

---

## 🚀 Step 5: Run the Server
1. Start the Flask application:
   ```bash
   python app.py
   ```
2. `Ctrl + Click` the link in the terminal (usually `http://127.0.0.1:5000`) to open it in your browser.
---

## 🧪 Step 6: Run the Test Suite

The project includes a comprehensive test suite covering all layers. Run it with:

```bash
python -m pytest tests/ -v
```

Tests are organized by layer:
| Test File | Covers |
|---|---|
| `test_config.py` | Config class, encapsulation, environment variables |
| `test_exceptions.py` | Custom exception hierarchy |
| `test_models.py` | User, CitizenUser, PublisherUser (inheritance + polymorphism) |
| `test_repository.py` | All repository classes with in-memory SQLite |
| `test_services.py` | Business logic layer with mock repositories |
| `test_upload.py` | FileUploadHelper file handling |
| `check_document_upload.py` | Document upload integration check |
| `check_readme_flow.py` | End-to-end README workflow verification |

---

## 🔑 Environment Variables (Optional)

The app works out of the box with defaults, but you can customize behaviour via environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `GOVKONEK_DB` | SQLite database file path | `govkonek.db` |
| `GOVKONEK_SECRET_KEY` | Flask session signing key | Auto-generated dev key |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key (optional) | *(not required — uses free Open-Meteo API)* |
| `GOVKONEK_UPLOAD_FOLDER` | Upload directory for documents/images | `static/uploads/` |

---

## 📡 API Endpoints Overview

The application exposes a full REST API consumed by the frontend templates:

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/register` | User registration form |
| `GET/POST` | `/login` | Login form (role-based redirect) |
| `GET` | `/logout` | Logout current user |

### Announcement Posts
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/posts` | List posts (supports `?search`, `?category`, `?sort`) |
| `GET` | `/api/posts/<id>` | Get post with comments & reactions |
| `POST` | `/api/posts` | Create post (publisher only) |
| `PUT` | `/api/posts/<id>` | Update post (owner only) |
| `DELETE` | `/api/posts/<id>` | Delete post (owner only) |
| `POST` | `/api/posts/<id>/comments` | Add comment |
| `POST` | `/api/posts/<id>/react` | Toggle emoji reaction |

### Projects
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/<id>` | Get single project |
| `POST` | `/api/projects` | Create project (publisher only) |
| `PUT` | `/api/projects/<id>` | Update project (owner only) |
| `DELETE` | `/api/projects/<id>` | Delete project (owner only) |

### Citizens' Voice (Community Forum)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/voice` | List voice posts (supports `?search`, `?sort`, `?category`, `?status`) |
| `GET` | `/api/voice/<id>` | Get voice post with comments & vote counts |
| `POST` | `/api/voice` | Create voice post (any authenticated user) |
| `PUT` | `/api/voice/<id>/status` | Update status (open/resolved/closed) |
| `DELETE` | `/api/voice/<id>` | Delete voice post (author only) |
| `POST` | `/api/voice/<id>/comments` | Add comment (publisher = official response) |
| `POST` | `/api/voice/<id>/vote` | Toggle up/down vote |

### Barangay Pages
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/barangays` | List all barangays |
| `GET` | `/api/barangays/<id>` | Get single barangay |
| `POST` | `/api/barangays` | Create barangay page (publisher only) |
| `PUT` | `/api/barangays/<id>` | Update barangay (owner only) |
| `DELETE` | `/api/barangays/<id>` | Delete barangay (owner only) |

### Other
| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/api/profile` | Get or update user profile |
| `GET` | `/api/services` | List e-services |
| `GET` | `/api/documents` | List transparency documents |
| `POST` | `/api/documents` | Upload document (publisher only) |
| `DELETE` | `/api/documents/<id>` | Delete document (publisher only) |
| `GET` | `/api/weather?lat=&lon=` | Live weather via Open-Meteo (free, no API key) |

---

## 📁 Project Structure
```
GovKonek-Flask-Project/
├── app.py              # Flask application factory with dependency injection
├── config.py           # Injectable Config class (ENCAPSULATION: @property)
├── exceptions.py       # Custom exception hierarchy (EXCEPTION HANDLING)
├── file_upload.py      # Centralized file upload handler (ABSTRACTION)
├── init_db.py          # Database initialization & seed data
├── models.py           # User, CitizenUser, PublisherUser (INHERITANCE + POLYMORPHISM)
├── repository.py       # Database layer — UserRepo, PostRepo, ProjectRepo, etc. (ABSTRACTION)
├── routes.py           # Flask HTTP routes (thin controllers) — 30+ endpoints
├── service.py          # Business logic — Auth, Post, Voice, Project, Document, Barangay services
├── templates/          # HTML templates (17 pages)
│   ├── components/     # Reusable UI components (feed, sidebar, weather, tracker, etc.)
│   └── static/
│       └── images/     # Static images (logo, etc.)
├── static/
│   └── uploads/        # User-uploaded files (ignored by Git)
└── tests/              # Unit & integration test suite (8 test files)
```

---

## 🏗️ Architecture & OOP Principles

The codebase is structured around the **four pillars of OOP**, with each layer testable in isolation via dependency injection:

| Layer | Files | OOP Principle |
|---|---|---|
| **Config** | `config.py` | Encapsulation — private attributes with `@property` accessors |
| **Models** | `models.py` | Inheritance + Polymorphism — `CitizenUser`/`PublisherUser` extend `User`, override `get_permissions()`/`can_publish()` |
| **Repository** | `repository.py` | Abstraction — `BaseRepository` with `DBContext` context manager hides SQLite details |
| **Service** | `service.py` | Abstraction — `BaseService` with shared validation helpers; services are repository-agnostic |
| **Routes** | `routes.py` | Thin controllers — routes access services via `current_app.extensions` (dependency injection) |
| **Exceptions** | `exceptions.py` | Exception Handling — domain-specific hierarchy (`GovKonekError` → `DatabaseError`, `ValidationError`, etc.) |
| **File Upload** | `file_upload.py` | Abstraction — hides file-system operations behind a simple `.save()` interface |