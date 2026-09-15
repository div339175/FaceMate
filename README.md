# FaceMate — secure face-recognition attendance

FaceMate is a Django attendance platform for schools and colleges. It provides
separate developer, teacher, and student portals; camera-assisted attendance;
manual review before finalisation; student attendance history; and CSV exports.

## Highlights

- Django password hashing with transparent upgrade of legacy demo passwords
- Role-based access: teachers can manage only their assigned class
- Face embeddings instead of retained enrollment photos
- Three-frame client verification before a roster is marked present
- Safe re-submission of a daily roster and database protection against duplicate
  student records within an attendance session
- Automated tests for sign-in, permissions, attendance totals, and constraints

## Run locally

Requirements: Python 3.9+ and pip. The first model download for DeepFace may
take a little longer.

```bash
git clone <your-repository-url>
cd facemate
chmod +x start.sh
./start.sh
```

On Windows PowerShell:

```powershell
./start.ps1
```

The scripts create a virtual environment, install dependencies, copy the sample
environment file when needed, run migrations, and start the server. Open
`http://127.0.0.1:8000/`.

For a quick local walkthrough, each login screen includes a **Try the demo**
button. Demo access is available only while `DJANGO_DEBUG=true`; it is disabled
automatically in production.

To create the first developer account, run this in another terminal after
activating the virtual environment:

```bash
python manage.py bootstrap_developer --name "Admin Name" --email admin@example.com
```

The command securely prompts for a password and never stores it in shell history.
Use the developer portal to add teachers, assign each teacher a class in the
`Class-Section` format (for example, `10-A`), and enroll students.

## Development checks

```bash
python manage.py migrate
python manage.py test
python manage.py check
```

## Configuration and deployment

Copy `.env.example` to `.env`. SQLite is the simple local default; MySQL can be
selected through the database variables in that file.

For a real deployment, use a managed database, generate a long unique
`DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=false`, restrict
`DJANGO_ALLOWED_HOSTS`, and serve the app over HTTPS. Only then set
`DJANGO_SECURE_COOKIES=true`, `DJANGO_SECURE_SSL_REDIRECT=true`, and a cautious
non-zero `DJANGO_SECURE_HSTS_SECONDS`. Do not commit `.env`, certificates,
databases, uploaded photos, or face embeddings.

The included Tailwind CDN is suitable for a demo. Build and self-host CSS before
a fully offline or tightly controlled production deployment.

## Biometric data

Review [PRIVACY.md](PRIVACY.md) before collecting student face data. Face
recognition should assist an authorized teacher—not replace review or a fair
manual attendance option.

## Architecture

```
Presentation Layer (Tailwind CSS, Vanilla JS, Camera Stream, Mutex Protection)
       ↓
Views & URL Routing (teacher/views.py, student/views.py, developer/views.py)
       ↓
Service Layer (attendance/services.py: atomic finalization, RBAC, CSV export)
       ↓
AI / Computer Vision Layer (core/face_utils.py: ArcFace embeddings, fast Haar/OpenCV detection)
       ↓
Data Layer (Django 5.2 ORM, SQLite / MySQL, unique constraints, transactional integrity)
```

## Troubleshooting Guide

### 1. Camera not opening in browser
- Browsers restrict camera access (`navigator.mediaDevices.getUserMedia`) to **HTTPS** or **`http://localhost`** / **`http://127.0.0.1`**.
- If testing on mobile or over a LAN IP (e.g. `http://192.168.x.x:8000`), the browser will block the camera unless served over HTTPS or via an SSL tunnel (such as ngrok or `django-sslserver`).
- FaceMate automatically displays a **Manual Attendance Mode** button if the camera is denied or unavailable so teachers can still complete attendance.

### 2. DeepFace weights or permission error on macOS
- FaceMate automatically redirects TensorFlow and DeepFace cache directories inside the workspace (`.keras` and `.deepface`) via `facemate/settings.py`.
- If running offline, live attendance uses OpenCV's built-in Haar cascade detector which runs locally in ~20ms and requires no weights download.

### 3. Port already in use (8000)
If port 8000 is occupied by another process:
```bash
python manage.py runserver 8080
```
or find and terminate the occupying PID:
```bash
lsof -ti :8000 | xargs kill -9
```

### 4. Attendance finalization & server responsiveness
- Live camera frames are governed by an in-flight mutex (`isProcessingFrame`) to prevent HTTP thread starvation.
- Video stream tracks and timers are automatically torn down when finalizing attendance or navigating back/away.
- Finalization is transactional (`transaction.atomic`) and idempotent.

### 5. Multi-Class Seeding
To populate realistic classes (`9-A`, `9-B`, `10-A`, `10-B`, `11-A`, `11-B`, `12-A`), teachers, students, and 7-day attendance records:
```bash
python manage.py seed_demo_data
```
