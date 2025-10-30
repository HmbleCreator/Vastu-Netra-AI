Running the Python backend locally
=================================

This backend is intended for local use (development or local Electron packaging).

Quick start (Windows)
---------------------

1. Create a virtual environment and activate it:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```cmd
pip install -r requirements.txt
```

3. Start the server:

```cmd
start-backend.bat
```

Quick start (macOS / Linux)
--------------------------

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start-backend.sh
```

Health check
------------

When the server is running you can check readiness from your Electron app (or curl):

```bash
curl http://127.0.0.1:8000/health
```

It returns a small JSON with service status and available routes.

Notes for Electron packaging
---------------------------
- You can start this backend as a child process from your Electron main process and use the `127.0.0.1:8000` endpoints for solver requests.
- Alternatively, you can port core solver modules to Node/TypeScript if you want a pure-JS bundle with no Python runtime.
