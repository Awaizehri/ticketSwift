# TicketSwift — Indie Theater & Comedy Show Box Office (FS-07)

[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20SQLite-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

**TicketSwift** is a web-based ticketing and box office management system designed for indie theaters and local comedy clubs. It allows patrons to browse showtimes, reserve seats with transactional locking guarantees to prevent double booking, and present digital, single-use QR-coded entry passes at the door.

---

## Project Milestones & Roadmap

- [x] **Module 1: Setup & Domain Architecture** — Environment split, custom User roles, data schema, migrations, admin registration, and seed data command.
- [ ] **Module 2: Booking Flow & Concurrency Controls**  Seat reservation view, `transaction.atomic` & `select_for_update` locking mechanisms, customer portal, and concurrent booking race condition tests.
- [ ] **Module 3: Scannable Tickets, Check-In & Manager Analytics**  Unique ticket hash generation, dynamic QR passes, door scanner validation API, and manager sales summary dashboard.
- [ ] **Module 4: Quality Assurance, Containerization & Live Deployment**  Comprehensive test coverage, Docker Compose containerization, and free-tier cloud deployment (Render + Neon PostgreSQL).

---

## System Architecture & Domain Model

The project is structured into domain-driven Django apps:
- `accounts`: Custom `User` model extending `AbstractUser` with role-based access (`customer` vs. `manager`).
- `shows`: Event catalog inventory (`Show`, `Showtime`, and unique physical `Seat` instances).
- `bookings`: Transactional records (`Order` holding one or more `Ticket` passes tied to reserved `Seat` items).

### ER Diagram
```
[User (accounts)] 
       │ 1:N
   [Order] ── 1:N ── [Ticket] ── 1:1 ── [Seat]
                                          │ N:1
                                     [Showtime]
                                          │ N:1
                                       [Show]
```

---

## Getting Started (Local Development)

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/Awaizehri/ticketSwift.git
cd ticketSwift
```

### 3. Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r ticketSwift/requirements.txt
```

### 5. Configure Environment Variables
Inside the inner `ticketSwift/ticketSwift/` directory (alongside `manage.py`), create a `.env` file:

```env
SECRET_KEY=your-secure-secret-key-here ## can generate it though django.core.utills 
DEBUG=True
```

*(Note: In development, Django defaults to SQLite. For production, PostgreSQL `DATABASE_URL` is configured).*

### 6. Apply Migrations
```bash
cd ticketSwift/ticketSwift
python manage.py migrate
```

### 7. Seed Demo Data
Populate shows, showtimes, seats, and test users:
```bash
python manage.py seed_data
```

### 8. Run the Development Server
```bash
python manage.py runserver
```
Visit the application:
- **Admin Panel**: `http://127.0.0.1:8000/admin`
- **Application Root**: `http://127.0.0.1:8000/`

---

## Demo Credentials (from `seed_data`)

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Manager / Admin** | `manager1` | `manager123` | Full Django Admin & Box Office management |
| **Customer** | `customer1` | `customer123` | Browsing & booking portal |

---

## Repository Structure

```text
ticketSwift/
├── .gitignore
├── README.md
└── ticketSwift/                     # Project root
    ├── manage.py
    ├── .env                         # Local secrets (ignored by Git)
    ├── requirements.txt
    ├── accounts/                    # Custom User and role logic
    ├── shows/                       # Shows, Showtimes, Seats & Seed command
    ├── bookings/                    # Orders & Tickets
    └── ticketSwift/                 # Configuration package
        ├── settings/
        │   ├── __init__.py
        │   ├── base.py              # Shared base configurations
        │   ├── local.py             # Development settings
        │   └── production.py        # Production & Cloud settings
        ├── urls.py
        └── wsgi.py
```
