# AutoDeploy — TaskFlow

A Kanban-style task manager built for a college DevOps project. You add tasks, drag them between **To Do → In Progress → Completed**, and everything is saved in a database.

## Objectives
- Build a small but real web application with a backend, database and front end.
- Add automated tests so every change can be checked quickly.
- Create a solid base that can later be used for CI/CD and containerisation (done separately).

## Features
- Sidebar navigation: Board, Due this week, High priority, Overdue, Completed
- Statistics: total, to do, in progress, completed, overdue
- Three Kanban columns with drag-and-drop (plus ← / → buttons for phones)
- Task cards with priority colour, due date and description
- Add, edit and delete tasks (with a delete confirmation)
- Live search and priority filter
- Empty states, success messages and error messages
- Responsive layout for desktop and mobile
- `/health` endpoint reporting server and database status

## Technology stack
| Part | Technology |
|------|-----------|
| Backend | Python + Flask |
| Database | SQLite (a single file, no setup) |
| Front end | HTML, CSS, JavaScript (no frameworks) |
| Testing | pytest |

## Folder structure
```text
autodeploy-taskflow/
├── app.py              # Flask backend: routes, validation, database code
├── requirements.txt    # Python packages needed
├── test_app.py         # Automated tests
├── .gitignore          # Files Git should ignore
├── README.md           # This file
├── instance/           # The SQLite database file is created here
│   └── .gitkeep
├── templates/
│   └── index.html      # Page structure
└── static/
    ├── css/style.css   # Styling
    └── js/app.js       # Interactivity (fetches data, drag-and-drop)
```

## Prerequisites
- Windows 10/11
- Python 3.10 or newer from https://www.python.org/downloads/ (tick **"Add Python to PATH"** during install)
- Visual Studio Code (optional but recommended)

Check Python is installed:
```powershell
python --version
```

## Setup on Windows
Open the project folder in VS Code, then open a terminal (**Terminal → New Terminal**).

**1. Create a virtual environment** (a private box of packages just for this project):
```powershell
python -m venv venv
```

**2. Activate it**

PowerShell:
```powershell
venv\Scripts\Activate.ps1
```
Command Prompt:
```cmd
venv\Scripts\activate.bat
```
You should see `(venv)` at the start of the terminal line.

> If PowerShell says "running scripts is disabled", run this once and try again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**3. Install the packages**
```powershell
pip install -r requirements.txt
```

## Run the app
```powershell
python app.py
```
Open **http://127.0.0.1:5000** in your browser. Press `Ctrl + C` in the terminal to stop it. Your tasks stay saved in `instance/taskflow.db`.

## Run the tests
```powershell
python -m pytest -v
```
Tests use a temporary database, so they never touch your real tasks.

## Important files explained
- **app.py** – Creates the Flask app, the `tasks` table, and all routes. `/api/...` routes return JSON; `/` shows the page; `/health` reports status. Input is checked in `validate()`, and every SQL query uses `?` placeholders (prevents SQL injection).
- **templates/index.html** – The page layout: sidebar, statistics, columns, and the pop-up forms.
- **static/js/app.js** – Talks to the API with `fetch`, draws the cards, handles drag-and-drop. Text is inserted with `textContent`, so malicious text such as `<script>` is shown harmlessly (prevents XSS). The server also sends a Content-Security-Policy header.
- **static/css/style.css** – Colours, layout and the mobile design.
- **test_app.py** – 22 tests covering pages, CRUD, filters, validation, missing tasks, health, and persistence.

## API summary
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/api/tasks?search=&status=&priority=` | List / search / filter |
| POST | `/api/tasks` | Create |
| GET / PUT / DELETE | `/api/tasks/<id>` | Read / edit / delete |
| PATCH | `/api/tasks/<id>/status` | Move between columns |
| GET | `/api/stats` | Counts for the dashboard |
| GET | `/health` | Health check |

## Troubleshooting
| Problem | Fix |
|---------|-----|
| `python` is not recognised | Reinstall Python and tick "Add Python to PATH", or try `py` instead of `python` |
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt |
| `No module named flask` | Activate the venv, then run `pip install -r requirements.txt` |
| Port 5000 already in use | Close the other program, or change the port in the last line of `app.py`: `run(debug=True, port=5001)` |
| Page looks unstyled | Hard refresh with `Ctrl + F5` |
| Want to reset all tasks | Stop the app and delete `instance/taskflow.db` |

## Screenshots
Add your own screenshots here:
- `![Board view](screenshots/board.png)`
- `![Add task dialog](screenshots/add-task.png)`
- `![Mobile view](screenshots/mobile.png)`
- `![Passing tests](screenshots/tests.png)`

## Future enhancements
- User accounts and login
- Task labels, assignees and comments
- Reordering cards within a column
- Dark mode
- Deployment with CI/CD and containers (planned as a separate stage)

IN FINAL

TO RUN THOSE : 

cd autodeploy-taskflow
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m pytest -v
python app.py

PASTE ALL THESE COMMANDS ON TO THE TERMINAL IN ORDER TO RUN THIS
THIS PROJECT IS PART OF MY PRACTICUM WORK THAT HELPS ME UNDERSTAND HOW DEVOPS PROJECT WORKS.
