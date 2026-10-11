# Vehicle Maintenance Index

A small, beginner-friendly app for keeping your vehicles and their maintenance history together. See what you own, what service has been done, what it cost, and the next service date when you have one.

## 🌐 Live Demo

- **Frontend:** https://ehicle-maintenance-index.vercel.app
- **Backend API:** https://vehicle-maintenance-api-5f73.onrender.com
- **API Documentation:** https://vehicle-maintenance-api-5f73.onrender.com/docs
- **Health Check:** https://vehicle-maintenance-api-5f73.onrender.com/health


## Features

- Register and log in with a password protected using Argon2, then receive a JWT for API access.
- Add, view, update, and delete your own vehicles.
- Record, edit, and delete service history with mileage, cost, notes, and optional next-service details.
- Mileage must stay non-decreasing per vehicle; lower readings are rejected with a message to correct the earlier entry.
- Attach receipt files (PDF/JPG/PNG/WebP up to 5 MB) to service records; only the vehicle owner can view or download them.
- Filter service history by service type or date and choose the date order.
- See service counts, the last service, and the next service on your dashboard.
- See total maintenance spending for a vehicle over the selected date range on the vehicle details page.
- New accounts see a helpful empty state with a clear action to add their first vehicle.
- Keep user data private through backend ownership checks.

## Tech stack

FastAPI · PostgreSQL · SQLAlchemy · Alembic · React · Vite · JWT · pwdlib + Argon2

## Requirements

- Python 3.11 or newer
- Node.js and npm
- PostgreSQL

## Backend setup

Create a database named `vehicle_maintenance` in PostgreSQL, then set up the API:

```bash
cd backend
python -m venv .venv
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

Install the backend packages:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the `backend` directory. Set `DATABASE_URL` to your PostgreSQL username, password, and database. Replace `SECRET_KEY` with a long random value.

Apply the initial database migration and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at <http://localhost:8000>. Interactive API documentation is at <http://localhost:8000/docs>.

## Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app at <http://localhost:5173>. It connects to the API at `http://localhost:8000` by default. To use a different API address, create `frontend/.env` with `VITE_API_URL=http://your-api-host`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the fork, branch, and pull request workflow.
