# GovKonek Flask Project — Architecture Diagrams

---

## 1. UML Class Diagram

```mermaid
classDiagram
    direction TB

    %% ────────────────────────────────────────────────────
    %% EXCEPTIONS
    %% ────────────────────────────────────────────────────
    class GovKonekError {
        +message: str
    }
    class DatabaseError {
        +original_error: Exception
    }
    class ConnectionError {
        +db_path: str
    }
    class RecordNotFoundError {
        +entity: str
        +identifier: str
    }
    class DuplicateRecordError {
        +entity: str
        +field: str
        +value: str
    }
    class AuthError
    class InvalidCredentialsError
    class RegistrationError
    class PermissionDeniedError
    class RequiredFieldError

    GovKonekError <|-- DatabaseError
    GovKonekError <|-- AuthError
    GovKonekError <|-- RequiredFieldError
    DatabaseError <|-- ConnectionError
    DatabaseError <|-- RecordNotFoundError
    DatabaseError <|-- DuplicateRecordError
    AuthError <|-- InvalidCredentialsError
    AuthError <|-- RegistrationError
    AuthError <|-- PermissionDeniedError

    %% ────────────────────────────────────────────────────
    %% CONFIG
    %% ────────────────────────────────────────────────────
    class Config {
        -_db_name: str
        -_secret_key: str
        -_login_view: str
        -_openweather_api_key: str
        -_upload_folder: str
        -_allowed_extensions: set
        +db_name: str (r)
        +secret_key: str (r)
        +login_view: str (r)
        +openweather_api_key: str (r)
        +upload_folder: str (r)
        +allowed_extensions: set (r)
    }

    %% ────────────────────────────────────────────────────
    %% DOMAIN MODELS  (models.py)
    %% ────────────────────────────────────────────────────
    class User {
        <<abstract>>
        -_id: int
        -_username: str
        -_role: str
        +id: int (r)
        +username: str (r)
        +role: str (r)
        +get_permissions()* list
        +can_publish()* bool
    }
    class CitizenUser {
        +get_permissions() list
        +can_publish() bool
    }
    class PublisherUser {
        +get_permissions() list
        +can_publish() bool
    }

    User <|-- CitizenUser : inherits
    User <|-- PublisherUser : inherits
    UserMixin <|-- User : inherits

    %% ────────────────────────────────────────────────────
    %% REPOSITORY LAYER  (repository.py)
    %% ────────────────────────────────────────────────────
    class DBContext {
        -_db_path: str
        -_connection: Connection
        +__enter__() Connection
        +__exit__() None
    }
    class BaseRepository {
        <<abstract>>
        -_db_path: str
        +_get_db() Connection
        +_execute(query, params, fetch, commit) any
        +_execute_write(query, params) cursor
    }
    class UserRepository {
        +find_by_id(user_id) Row
        +find_by_username(username) Row
        +create(username, hash, role) bool
    }
    class PostRepository {
        +get_all_posts(...) list
        +get_post_by_id(id) Row
        +create_post(...) dict
        +update_post(id, user_id, title, content) dict
        +delete_post(id, user_id) None
        +get_comments_for_post(id) list
        +add_comment(post_id, user_id, content) dict
        +get_reactions_for_post(id) list
        +toggle_reaction(post_id, user_id, emoji) tuple
        +get_user_reaction(post_id, user_id) str
        +get_posts_by_publisher(id) list
    }
    class ProjectRepository {
        +get_all() list
        +get_by_id(id) Row
        +get_by_publisher(id) list
        +create(...) dict
        +update(id, ...) dict
        +delete(id, user_id) None
    }
    class ServiceRepository {
        +get_all() list
    }
    class DocumentRepository {
        +get_all() list
        +create(filename, url) bool
    }
    class VoiceRepository {
        +get_all(...) list
        +get_by_id(id) dict
        +create(user_id, title, content, category) dict
        +delete(id, user_id) None
        +update_status(id, status) None
        +get_comments(id) list
        +add_comment(id, user_id, content, official) dict
        +toggle_vote(id, user_id, type) tuple
        +get_user_vote(id, user_id) str
    }
    class BarangayRepository {
        +get_all() list
        +get_by_id(id) Row
        +get_by_publisher(id) Row
        +get_first() Row
        +create(...) dict
        +update(id, ...) None
    }

    BaseRepository <|-- UserRepository
    BaseRepository <|-- PostRepository
    BaseRepository <|-- ProjectRepository
    BaseRepository <|-- ServiceRepository
    BaseRepository <|-- DocumentRepository
    BaseRepository <|-- VoiceRepository
    BaseRepository <|-- BarangayRepository

    %% ────────────────────────────────────────────────────
    %% SERVICE LAYER  (service.py)
    %% ────────────────────────────────────────────────────
    class BaseService {
        <<abstract>>
        +_require(value, field_name)$ void
        +_validate_choice(value, field, allowed)$ any
        +_check_publisher(user)$ void
        +_sanitize(value)$ str
    }
    class AuthService {
        -_user_repo: UserRepository
        +register_user(username, password, role) tuple
        +authenticate_user(username, password) tuple
    }
    class PostService {
        -_post_repo: PostRepository
        +get_feed(search, category, sort) list
        +get_post_detail(post_id, user_id) dict
        +add_comment(post_id, user_id, content) tuple
        +toggle_reaction(post_id, user_id, emoji) tuple
        +create_post(user, title, content, ...) tuple
        +update_post(user, post_id, title, content) tuple
        +delete_post(user, post_id) tuple
    }
    class VoiceService {
        -_repo: VoiceRepository
        +get_posts(...) list
        +get_post_detail(id, user_id) dict
        +create_post(user_id, title, content, category) tuple
        +update_status(id, status) tuple
        +delete_post(id, user_id) tuple
        +add_comment(id, user_id, content, role) tuple
        +toggle_vote(id, user_id, type) tuple
        +get_categories() list
    }
    class ProjectService {
        -_repo: ProjectRepository
        +create_project(user, ...) tuple
        +update_project(user, id, ...) tuple
        +delete_project(user, id) tuple
    }
    class DocumentService {
        -_repo: DocumentRepository
        -_config: Config
        +upload(...) tuple
        +get_all() list
    }
    class BarangayService {
        -_repo: BarangayRepository
        +get_by_publisher(id) Row
        +get_first() Row
        +get_by_id(id) Row
    }

    BaseService <|-- AuthService
    BaseService <|-- PostService
    BaseService <|-- VoiceService
    BaseService <|-- ProjectService
    BaseService <|-- DocumentService
    BaseService <|-- BarangayService

    %% ────────────────────────────────────────────────────
    %% UTILITIES
    %% ────────────────────────────────────────────────────
    class FileUploadHelper {
        -_upload_dir: str
        -_allowed_extensions: set
        +save(file, prefix, exts) str
        +delete(url_path) bool
    }

    %% ────────────────────────────────────────────────────
    %% RELATIONSHIPS: Service → Repository (injection)
    %% ────────────────────────────────────────────────────
    AuthService --> UserRepository : uses
    PostService --> PostRepository : uses
    VoiceService --> VoiceRepository : uses
    ProjectService --> ProjectRepository : uses
    DocumentService --> DocumentRepository : uses
    DocumentService --> Config : uses
    BarangayService --> BarangayRepository : uses

    %% ────────────────────────────────────────────────────
    %% FACTORY
    %% ────────────────────────────────────────────────────
    note for create_user_from_db "Factory Function: maps role → CitizenUser | PublisherUser"
```

---

## 2. MVC Architecture Diagram (Layered View)

```mermaid
graph TB
    subgraph "CLIENT (Browser)"
        CLIENT["🌐 Web Browser<br/><i>HTML / CSS / JavaScript</i>"]
    end

    subgraph "VIEW LAYER — templates/"
        direction LR
        BASE["base.html<br/><i>master layout</i>"]
        LOGIN["login.html<br/>register.html"]
        DASH["dashboard.html<br/>profile.html"]
        BARANGAY["barangay_landing.html<br/>barangay_map.html<br/>barangay_profile.html"]
        CONTENT["projects.html<br/>services.html<br/>documents.html<br/>post_detail.html<br/>citizens_voice.html<br/>service_placeholder.html"]
        COMP["components/<br/>admin_ledger.html<br/>display_post.html<br/>feed.html<br/>sidebar.html<br/>tracker.html<br/>utility_bar.html<br/>weather.html"]
        BASE --> LOGIN
        BASE --> DASH
        BASE --> BARANGAY
        BASE --> CONTENT
        CONTENT --> COMP
    end

    subgraph "CONTROLLER LAYER — routes.py"
        direction TB
        AUTH_R["/login, /register, /logout"]
        PAGES_R["/dashboard, /profile<br/>/barangay-landing, /barangay-map<br/>/projects, /services, /documents<br/>/post/&lt;id&gt;, /barangay/&lt;id&gt;<br/>/citizens-voice, /barangay/view/&lt;slug&gt;"]
        API_R["/api/posts (CRUD)<br/>/api/projects (CRUD)<br/>/api/services, /api/documents<br/>/api/profile, /api/voice/*<br/>/api/weather, /api/upload"]
        AUTH_R --> PAGES_R --> API_R
    end

    subgraph "SERVICE LAYER — service.py"
        direction LR
        AuthSvc["AuthService<br/><i>register, authenticate</i>"]
        PostSvc["PostService<br/><i>feed, comments, reactions</i>"]
        VoiceSvc["VoiceService<br/><i>forum, grievances, votes</i>"]
        ProjectSvc["ProjectService<br/><i>CRUD barangay projects</i>"]
        DocSvc["DocumentService<br/><i>transparency uploads</i>"]
        BarangaySvc["BarangayService<br/><i>barangay lookup</i>"]
    end

    subgraph "REPOSITORY LAYER — repository.py"
        direction LR
        UserRepo["UserRepository"]
        PostRepo["PostRepository"]
        VoiceRepo["VoiceRepository"]
        ProjectRepo["ProjectRepository"]
        ServiceRepo["ServiceRepository"]
        DocRepo["DocumentRepository"]
        BarangayRepo["BarangayRepository"]
        DB["DBContext<br/><i>connection manager</i>"]
    end

    subgraph "DOMAIN MODELS — models.py"
        direction LR
        UserM["User ◀ ABC"]
        CitizenU["CitizenUser"]
        PublisherU["PublisherUser"]
        Factory["create_user_from_db()"]
        UserM --> CitizenU
        UserM --> PublisherU
        Factory --> CitizenU
        Factory --> PublisherU
    end

    subgraph "INFRASTRUCTURE"
        direction LR
        CFG["Config<br/><i>db_name, secret_key, uploads</i>"]
        EXC["Exceptions<br/>GovKonekError ▶ DatabaseError ▶ AuthError"]
        UPLOAD["FileUploadHelper<br/><i>file save / delete</i>"]
        SQLITE[("🗄️ SQLite<br/>govkonek.db")]
    end

    %% ── FLOW ──────────────────────────────────────────
    CLIENT <-->|"HTTP req / res"| AUTH_R
    CLIENT <-->|"HTTP req / res"| PAGES_R
    CLIENT <-->|"JSON API"| API_R

    AUTH_R -->|"calls"| AuthSvc
    PAGES_R -->|"calls"| PostSvc
    PAGES_R -->|"calls"| BarangaySvc
    API_R -->|"calls"| PostSvc
    API_R -->|"calls"| VoiceSvc
    API_R -->|"calls"| ProjectSvc
    API_R -->|"calls"| DocSvc

    AuthSvc -->|"queries"| UserRepo
    PostSvc -->|"queries"| PostRepo
    VoiceSvc -->|"queries"| VoiceRepo
    ProjectSvc -->|"queries"| ProjectRepo
    DocSvc -->|"queries"| DocRepo
    BarangaySvc -->|"queries"| BarangayRepo

    UserRepo --> DB
    PostRepo --> DB
    VoiceRepo --> DB
    ProjectRepo --> DB
    ServiceRepo --> DB
    DocRepo --> DB
    BarangayRepo --> DB
    DB --> SQLITE

    AuthSvc -.->|"creates"| Factory
    UserRepo -.->|"provides raw row"| Factory

    CFG -.->|"injected into"| DocSvc
    CFG -.->|"configures"| AUTH_R
    UPLOAD -.->|"used by"| API_R
    EXC -.->|"raised by"| AuthSvc
    EXC -.->|"raised by"| PostSvc
```

---

## 3. Request Lifecycle (Sequence Diagram)

```mermaid
sequenceDiagram
    actor Citizen
    participant Browser
    participant Flask as Flask Routes<br/>(Controller)
    participant Service as Service Layer<br/>(Business Logic)
    participant Repo as Repository Layer<br/>(Data Access)
    participant DB as SQLite<br/>(govkonek.db)
    participant Template as Jinja2 Templates<br/>(View)

    Citizen->>Browser: Opens /dashboard
    Browser->>Flask: GET /dashboard
    Flask->>Flask: @login_required → load_user()
    Flask->>Repo: user_repo.find_by_id(user_id)
    Repo->>DB: SELECT * FROM users WHERE id=?
    DB-->>Repo: Row {id, username, role}
    Repo-->>Flask: user_data
    Flask->>Flask: create_user_from_db() → CitizenUser
    Flask->>Service: barangay_repo.get_by_publisher()
    Service->>Repo: query
    Repo->>DB: SELECT ...
    DB-->>Repo: Row
    Repo-->>Service: barangay
    Service-->>Flask: barangay
    Flask->>Template: render_template('dashboard.html', ...)
    Template-->>Flask: rendered HTML
    Flask-->>Browser: 200 OK (HTML)
    Browser-->>Citizen: Dashboard page
```

---

## 4. Dependency Injection Container

```mermaid
graph LR
    subgraph "app.py — create_app()"
        direction TB
        CFG_INST["Config(db_name, secret_key, ...)"]
        BUILD["_build_services(app, config)"]
        LOGIN_MGR["setup_login_manager(app)"]
        ROUTES["create_routes(app)"]
    end

    subgraph "_build_services() — Wire Dependencies"
        direction TB
        UR["UserRepository(db_path)"]
        PR["PostRepository(db_path)"]
        ProjR["ProjectRepository(db_path)"]
        SR["ServiceRepository(db_path)"]
        DR["DocumentRepository(db_path)"]
        VR["VoiceRepository(db_path)"]
        BR["BarangayRepository(db_path)"]
        AS["AuthService(user_repo=UR)"]
        PS["PostService(post_repo=PR)"]
        VS["VoiceService(voice_repo=VR)"]
        ProjS["ProjectService(project_repo=ProjR)"]
        DS["DocumentService(document_repo=DR, config=cfg)"]
        BS["BarangayService(barangay_repo=BR)"]
    end

    CFG_INST --> BUILD
    UR --> AS
    PR --> PS
    VR --> VS
    ProjR --> ProjS
    DR --> DS
    BR --> BS

    subgraph "app.extensions (DI Container)"
        EXT["{<br/>config, user_repo, post_repo,<br/>project_repo, service_repo,<br/>document_repo, voice_repo,<br/>barangay_repo, auth_service,<br/>post_service, voice_service,<br/>project_service, document_service,<br/>barangay_service<br/>}"]
    end

    BUILD --> EXT
    EXT --> ROUTES
```

---

### Key Architectural Patterns

| Pattern | Where | Benefit |
|---------|-------|---------|
| **MVC** | routes → service → repository → templates | Separation of concerns |
| **Dependency Injection** | `app.py` → `_build_services()` | Testable, swappable implementations |
| **Repository Pattern** | `repository.py` (BaseRepository + 7 subclasses) | Isolates DB access, easy to swap SQLite for PostgreSQL |
| **Service Layer** | `service.py` (BaseService + 6 subclasses) | Business logic independent of HTTP |
| **Factory Pattern** | `create_user_from_db()` in `models.py` | Polymorphic User creation from DB rows |
| **Template Method** | `BaseRepository._execute()` / `BaseService` helpers | Shared behavior defined once |
| **Context Manager** | `DBContext` | Automatic connection cleanup |
| **OOP Pillars** | Encapsulation (private attrs + @property), Inheritance (Base* → subclasses), Polymorphism (CitizenUser vs PublisherUser), Abstraction (ABCs) | Maintainable, extensible codebase |
