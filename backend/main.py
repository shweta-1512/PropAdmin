from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional

import os
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DB = Path(__file__).with_name("propadmin.db")
load_dotenv(Path(__file__).with_name(".env"))

SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET missing or too short in backend/.env")

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60


app = FastAPI(title="PropAdmin API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

# JWT authentication
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in."
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token."
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token."
        )

    with conn() as c:
        user = c.execute(
            "SELECT id, name, email, role, status FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    if user is None or user["status"] != "Active":
        raise HTTPException(
            status_code=401,
            detail="User account is not active. Please log in again."
        )

    return dict(user)

# Role-based authorization
def require_roles(*allowed_roles):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action."
            )
        return current_user
    return role_checker


# DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():
    with conn() as c:

        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Customer',
            status TEXT NOT NULL DEFAULT 'Pending',
            phone TEXT DEFAULT '',
            project_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            organisation TEXT DEFAULT '',
            address TEXT DEFAULT '',
            status TEXT DEFAULT 'Active'
        );

        CREATE TABLE IF NOT EXISTS roles(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'General',
            category TEXT DEFAULT 'Other - General',
            related_asset TEXT DEFAULT '',
            project_id INTEGER,
            assigned_to TEXT DEFAULT '',
            expected_date TEXT DEFAULT '',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS complaints(
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            project_id INTEGER,
            reported_by TEXT DEFAULT '',
            assigned_to TEXT DEFAULT '',
            expected_date TEXT DEFAULT '',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS compliances(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            project_id INTEGER,
            responsible_person TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending',
            evidence TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS audit_log(
            id INTEGER PRIMARY KEY,
            action TEXT,
            actor TEXT,
            detail TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Add columns to an existing tasks table.
        # Existing task records will be preserved.

        task_columns = {
            row["name"]
            for row in c.execute(
                "PRAGMA table_info(tasks)"
            ).fetchall()
        }

        if "category" not in task_columns:
            c.execute("""
                ALTER TABLE tasks
                ADD COLUMN category TEXT DEFAULT 'Other - General'
            """)

        if "related_asset" not in task_columns:
            c.execute("""
                ALTER TABLE tasks
                ADD COLUMN related_asset TEXT DEFAULT ''
            """)

        # Default users

        defaults = [
            (
                "Super Admin",
                "admin@propadmin.in",
                "Admin@123",
                "Super Admin",
                "Active"
            ),
            (
                "Property Manager",
                "manager@propadmin.in",
                "Manager@123",
                "Manager",
                "Active"
            ),
            (
                "Client User",
                "client@propadmin.in",
                "Client@123",
                "Customer",
                "Active"
            ),
        ]

        for name, email, password, role, status in defaults:
            c.execute(
                """
                INSERT OR IGNORE INTO users
                (name, email, password_hash, role, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    hash_pw(password),
                    role,
                    status
                )
            )

        # Default roles

        default_roles = [
            "Super Admin",
            "Admin",
            "Manager",
            "Customer",
            "Vendor",
            "Accountant",
            "Technical Staff",
            "Help Desk",
            "Back-End"
        ]

        for role in default_roles:
            c.execute(
                "INSERT OR IGNORE INTO roles(name) VALUES(?)",
                (role,)
            )


init_db()


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class Login(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "Customer"
    phone: str = ""
    project_id: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str
    organisation: str = ""
    address: str = ""


class RoleCreate(BaseModel):
    name: str
    description: str = ""


class TaskCreate(BaseModel):
    title: str
    type: str = "General"

    category: str = "Other - General"

    # Optional asset field
    related_asset: str = ""

    project_id: Optional[int] = None
    assigned_to: str = ""
    expected_date: str = ""
    priority: str = "Medium"
    description: str = ""


class ComplaintCreate(BaseModel):
    title: str
    project_id: Optional[int] = None
    reported_by: str = ""
    assigned_to: str = ""
    expected_date: str = ""
    priority: str = "Medium"
    description: str = ""


class ComplianceCreate(BaseModel):
    name: str
    project_id: Optional[int] = None
    responsible_person: str = ""
    due_date: str = ""
    evidence: str = ""


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def rows(table):
    allowed_tables = {
        "users",
        "projects",
        "roles",
        "tasks",
        "complaints",
        "compliances",
        "audit_log"
    }

    if table not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail="Invalid table"
        )

    with conn() as c:
        result = c.execute(
            f"SELECT * FROM {table} ORDER BY id DESC"
        )

        return [dict(row) for row in result]


def audit(action, actor, detail):
    with conn() as c:
        c.execute(
            """
            INSERT INTO audit_log(action, actor, detail)
            VALUES (?, ?, ?)
            """,
            (action, actor, detail)
        )


# --------------------------------------------------
# GENERAL ROUTES
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "app": "PropAdmin",
        "status": "running"
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


 
# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.post("/api/login")
def login(data: Login):

    with conn() as c:
        user = c.execute(
            "SELECT * FROM users WHERE email = ?",
            (data.email.strip().lower(),)
        ).fetchone()

    if (
        not user
        or user["password_hash"] != hash_pw(data.password)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if user["status"] != "Active":
        raise HTTPException(
            status_code=403,
            detail="Your account is pending approval or inactive."
        )

    # Generate JWT token
    now = datetime.now(timezone.utc)

    token_payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    }

    access_token = jwt.encode(
        token_payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"]
    }


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.post("/api/register")
def register(data: UserCreate):

    with conn() as c:
        try:
            cur = c.execute(
                """
                INSERT INTO users
                (name, email, password_hash, role, status, phone, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.name,
                    data.email.strip().lower(),
                    hash_pw(data.password),
                    data.role,
                    "Pending",
                    data.phone,
                    data.project_id
                )
            )

            user_id = cur.lastrowid

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )

    audit(
        "User registration",
        "Self-service",
        f"New pending user: {data.email}"
    )

    return {
        "id": user_id,
        "status": "Pending",
        "message": "Registration submitted. Wait for Super Admin approval."
    }


# --------------------------------------------------
# USER MANAGEMENT
# --------------------------------------------------


@app.get("/api/users")
def get_users(
    current_user: dict = Depends(
        require_roles("Super Admin")
    )
):
    users = rows("users")

    return [
        {
            key: value
            for key, value in user.items()
            if key != "password_hash"
        }
        for user in users
    ]


@app.post("/api/users")
def create_user(data: UserCreate):

    with conn() as c:
        try:
            cur = c.execute(
                """
                INSERT INTO users
                (name, email, password_hash, role, status, phone, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.name,
                    data.email.strip().lower(),
                    hash_pw(data.password),
                    data.role,
                    "Pending",
                    data.phone,
                    data.project_id
                )
            )

            user_id = cur.lastrowid

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )

    audit(
        "Create user",
        "Super Admin",
        data.email
    )

    return {
        "id": user_id,
        "status": "Pending",
        "message": "User created and is awaiting approval."
    }


# --------------------------------------------------
# PENDING APPROVALS
# --------------------------------------------------


@app.get("/api/users/pending")
def get_pending_users(
    current_user: dict = Depends(
        require_roles("Super Admin")
    )
):
    with conn() as c:
        result = c.execute(
            """
            SELECT id, name, email, role, status, phone, project_id
            FROM users
            WHERE status = 'Pending'
            ORDER BY id DESC
            """
        )

        return [dict(user) for user in result]



@app.post("/api/users/{uid}/approve")
def approve_user(
    uid: int,
    current_user: dict = Depends(
        require_roles("Super Admin")
    )
):


    with conn() as c:
        cur = c.execute(
            """
            UPDATE users
            SET status = 'Active'
            WHERE id = ? AND status = 'Pending'
            """,
            (uid,)
        )

        if not cur.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Pending user not found"
            )

    audit(
        "Approve user",
        "Super Admin",
        str(uid)
    )

    return {
        "message": "User approved successfully",
        "status": "Active"
    }


@app.post("/api/users/{uid}/reject")
def reject_user(uid: int):

    with conn() as c:
        cur = c.execute(
            """
            UPDATE users
            SET status = 'Rejected'
            WHERE id = ? AND status = 'Pending'
            """,
            (uid,)
        )

        if not cur.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Pending user not found"
            )

    audit(
        "Reject user",
        "Super Admin",
        str(uid)
    )

    return {
        "message": "User rejected",
        "status": "Rejected"
    }


# --------------------------------------------------
# PROJECT MANAGEMENT
# --------------------------------------------------

@app.get("/api/projects")
def get_projects():
    return rows("projects")


@app.post("/api/projects")
def create_project(data: ProjectCreate):

    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO projects(name, organisation, address)
            VALUES (?, ?, ?)
            """,
            (
                data.name,
                data.organisation,
                data.address
            )
        )

        project_id = cur.lastrowid

    audit(
        "Create project",
        "Super Admin",
        data.name
    )

    return {
        "id": project_id,
        "message": "Project created"
    }


# --------------------------------------------------
# ROLE MANAGEMENT
# --------------------------------------------------

@app.get("/api/roles")
def get_roles():
    return rows("roles")


@app.post("/api/roles")
def create_role(data: RoleCreate):

    with conn() as c:
        try:
            cur = c.execute(
                """
                INSERT INTO roles(name, description)
                VALUES (?, ?)
                """,
                (
                    data.name,
                    data.description
                )
            )

            role_id = cur.lastrowid

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Role already exists"
            )

    return {
        "id": role_id,
        "message": "Role created"
    }


# --------------------------------------------------
# TASK MANAGEMENT
# --------------------------------------------------

TASK_CATEGORIES = [
    "Admin, Office",
    "Security and Safety",
    "Housekeeping and Hygiene",
    "Repair and Maintenance",
    "Other - General"
]


@app.get("/api/task-categories")
def get_task_categories():
    return TASK_CATEGORIES


@app.get("/api/tasks")
def get_tasks():
    return rows("tasks")


@app.post("/api/tasks")
def create_task(data: TaskCreate):

    if data.category not in TASK_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid task category"
        )

    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO tasks (
                title,
                type,
                category,
                related_asset,
                project_id,
                assigned_to,
                expected_date,
                priority,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.title,
                data.type,
                data.category,
                data.related_asset,
                data.project_id,
                data.assigned_to,
                data.expected_date,
                data.priority,
                data.description
            )
        )

        task_id = cur.lastrowid

    audit(
        "Create task",
        data.assigned_to or "Unassigned",
        data.title
    )

    return {
        "id": task_id,
        "message": "Task created successfully"
    }


@app.patch("/api/tasks/{tid}")
def update_task(tid: int, status: str):

    with conn() as c:
        cur = c.execute(
            """
            UPDATE tasks
            SET status = ?
            WHERE id = ?
            """,
            (status, tid)
        )

        if not cur.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

    return {"message": "Task updated"}


# --------------------------------------------------
# COMPLAINT MANAGEMENT
# --------------------------------------------------

@app.get("/api/complaints")
def get_complaints():
    return rows("complaints")


@app.post("/api/complaints")
def create_complaint(data: ComplaintCreate):

    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO complaints
            (title, project_id, reported_by, assigned_to,
             expected_date, priority, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.title,
                data.project_id,
                data.reported_by,
                data.assigned_to,
                data.expected_date,
                data.priority,
                data.description
            )
        )

        complaint_id = cur.lastrowid

    audit(
        "Create complaint",
        data.reported_by,
        data.title
    )

    return {
        "id": complaint_id,
        "message": "Complaint created"
    }


# --------------------------------------------------
# COMPLIANCE MANAGEMENT
# --------------------------------------------------

@app.get("/api/compliances")
def get_compliances():
    return rows("compliances")


@app.post("/api/compliances")
def create_compliance(data: ComplianceCreate):

    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO compliances
            (name, project_id, responsible_person, due_date, evidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data.name,
                data.project_id,
                data.responsible_person,
                data.due_date,
                data.evidence
            )
        )

        compliance_id = cur.lastrowid

    audit(
        "Create compliance",
        data.responsible_person,
        data.name
    )

    return {
        "id": compliance_id,
        "message": "Compliance created"
    }


# --------------------------------------------------
# AUDIT LOG
# --------------------------------------------------

@app.get("/api/audit")
def get_audit():
    return rows("audit_log")


# --------------------------------------------------
# SUPER ADMIN APPROVAL APIs
# --------------------------------------------------

def update_approval_status(table, record_id, new_status, action):
    allowed_tables = {
        "tasks",
        "complaints",
        "compliances"
    }

    if table not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail="Invalid table"
        )

    with conn() as c:
        cur = c.execute(
            f"UPDATE {table} SET status = ? WHERE id = ?",
            (new_status, record_id)
        )

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

    audit(
        action,
        "Super Admin",
        f"{table} ID: {record_id}, Status: {new_status}"
    )

    return {
        "id": record_id,
        "status": new_status,
        "message": f"{table.capitalize()} {new_status.lower()} successfully"
    }


# ---------------- TASK APPROVAL ----------------

@app.post("/api/tasks/{tid}/approve")
def approve_task(tid: int):
    return update_approval_status(
        "tasks",
        tid,
        "Approved",
        "Approve task"
    )


@app.post("/api/tasks/{tid}/reject")
def reject_task(tid: int):
    return update_approval_status(
        "tasks",
        tid,
        "Rejected",
        "Reject task"
    )


# ---------------- COMPLAINT APPROVAL ----------------

@app.post("/api/complaints/{cid}/approve")
def approve_complaint(cid: int):
    return update_approval_status(
        "complaints",
        cid,
        "Approved",
        "Approve complaint"
    )


@app.post("/api/complaints/{cid}/reject")
def reject_complaint(cid: int):
    return update_approval_status(
        "complaints",
        cid,
        "Rejected",
        "Reject complaint"
    )


# ---------------- COMPLIANCE APPROVAL ----------------

@app.post("/api/compliances/{cid}/approve")
def approve_compliance(cid: int):
    return update_approval_status(
        "compliances",
        cid,
        "Approved",
        "Approve compliance"
    )


@app.post("/api/compliances/{cid}/reject")
def reject_compliance(cid: int):
    return update_approval_status(
        "compliances",
        cid,
        "Rejected",
        "Reject compliance"
    )