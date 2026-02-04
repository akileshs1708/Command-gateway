# Command Gateway System

A secure command execution gateway with role-based access control, credit system, and full audit logging.

## 🏗️ Architecture

```
command-gateway/
│
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLite connection & session handling
│   ├── models.py            # DB models: User, Rule, Command, AuditLog
│   ├── auth.py              # API key authentication & role checks
│   ├── rules.py             # Rule matching logic (regex engine)
│   └── commands.py          # Command submission & execution logic
│
├── frontend/
│   ├── index.html           # UI page
│   ├── styles.css           # Basic styling
│   └── script.js            # API calls & UI updates
│
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── command_gateway.db      # SQLite database (auto-created)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

```bash
cd backend
python main.py
```

Or with uvicorn directly:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### 3. Open the Frontend

Open `frontend/index.html` in your web browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000`

### 4. Login

Use the default admin credentials:
- **API Key**: `admin-key-12345`

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 API Endpoints

### Member Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/commands` | Submit a command for execution |
| GET | `/credits` | Get current credit balance |
| GET | `/history` | Get command history |
| GET | `/me` | Get current user info |
| GET | `/rules` | View all rules |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rules` | Create a new rule |
| DELETE | `/rules/{id}` | Delete a rule |
| POST | `/users` | Create a new user |
| GET | `/users` | List all users |
| PUT | `/users/{id}/credits` | Adjust user credits |
| GET | `/audit-logs` | View audit logs |
| GET | `/commands/all` | View all commands |

## 🔒 Authentication

All API requests require the `X-API-Key` header:

```bash
curl -H "X-API-Key: admin-key-12345" http://localhost:8000/me
```

## 📜 Default Rules

The system is seeded with these default rules:

| Pattern | Action | Description |
|---------|--------|-------------|
| `rm\s+-rf\s+/` | AUTO_REJECT | Block recursive delete of root |
| `mkfs` | AUTO_REJECT | Block filesystem formatting |
| `dd\s+if=.*of=/dev/` | AUTO_REJECT | Block direct disk writes |
| `^git\s+(status\|log\|diff)` | AUTO_ACCEPT | Allow safe git commands |
| `^(ls\|cat\|pwd\|whoami)` | AUTO_ACCEPT | Allow basic info commands |

## 💳 Credit System

- Each user starts with 100 credits
- Executing a command costs 1 credit
- Rejected commands do NOT deduct credits
- Admins can adjust user credits

## 🔄 Command Flow

1. User submits command via API
2. System authenticates user via API key
3. System checks if user has credits > 0
4. Command is matched against rules (by priority)
5. Based on matched rule:
   - **AUTO_ACCEPT**: Command is "executed" (mocked)
   - **AUTO_REJECT**: Command is rejected
   - **No match**: Command is rejected by default
6. Credits are deducted only on successful execution
7. All actions are logged in audit trail

## 🧪 Testing Commands

### Safe Commands (should execute):
```bash
ls -la
git status
pwd
whoami
date
echo hello
```

### Dangerous Commands (should be rejected):
```bash
rm -rf /
mkfs.ext4 /dev/sda
dd if=/dev/zero of=/dev/sda
```

## 🛡️ Security Features

- API key authentication
- Role-based access control (Admin/Member)
- Command pattern matching with regex
- Credit-based rate limiting
- Full audit trail
- Transactional integrity (all-or-nothing operations)
- Commands are mocked, never actually executed

## 📊 Transaction Guarantees

All command operations are transactional:
- Credit deduction
- Command record creation
- Audit log entry

If any step fails, all changes are rolled back.

## 🐛 Troubleshooting

### CORS Issues
If you get CORS errors, make sure:
1. The backend is running on port 8000
2. You're accessing the frontend from a local server (not file://)

### Database Reset
To reset the database, simply delete `command_gateway.db`:
```bash
rm command_gateway.db
```

The database will be recreated on next server start.

## 📝 License

MIT License
