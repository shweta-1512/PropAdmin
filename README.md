# PropAdmin — Full-Stack Starter

A single-command Windows starter for a role-based property operations portal.

## Requirements
- Python 3.10+
- Node.js 18+ (20 LTS recommended)

## Run
Open PowerShell in this folder and run:

```powershell
python start-all.py
```

Then open:
- Frontend: http://localhost:5173
- Backend API docs: http://127.0.0.1:8000/docs

On first run the launcher creates `backend/.venv`, installs Python dependencies, and installs frontend dependencies.

## Demo accounts
- Super Admin: `admin@propadmin.in` / `Admin@123`
- Manager: `manager@propadmin.in` / `Manager@123`
- Client: `client@propadmin.in` / `Client@123`

## Included
- Login and role-based navigation
- New user registration creates a `Pending` account
- Super Admin Pending Approvals screen
- User approval/rejection
- User, project, role, task, complaint and compliance records
- SQLite persistence
- Simple dashboards and API documentation

## Important
This is a development starter, not a production-ready system. Before production, implement password reset and 2FA, email/SMS delivery, stronger session/token handling, CSRF protections, detailed per-record authorization, backups, HTTPS, and a production database. Change demo passwords and secrets. Do not commit `.env` files or real user data.
