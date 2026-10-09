# Campus Customs Operations Dashboard (hw5)

This project is a Campus Customs operations dashboard with a FastAPI backend, a React/Vite operations board, and a FastMCP server. The seeded SQLite databases are included:

- `data/campus_customs.db` — original populated snapshot
- `data/campus_customs_new.db` — working database used by the MCP server and backend

The empty `data/campus.customs.db` file is not used and is intentionally not included.

## Setup

From this folder, create and activate a virtual environment, then install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you want AI-powered ticket analysis, create a local `.env` file with your provider key. Never commit it:

```bash
cp .env.example .env
```

Set `PORTKEY_API_KEY` in `.env` (or in your shell environment). The application uses the configured Portkey/OpenAI-compatible provider and the `GPT5.6-Luna` model.

## Start the MCP server

With the virtual environment active, start the local FastMCP server in a separate terminal:

```bash
fastmcp run mcp_server/server.py
```

The server uses the read-only tools in `mcp_server/server.py` and reads from `data/campus_customs_new.db`.

## Start the FastAPI backend

In another terminal, from the project root:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

The API is available at `http://127.0.0.1:8000`.

## Start the React board

In a third terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## Reset before a full three-ticket run

Always reset the working database before running tickets 101, 102, and 103 as a clean full run. Make sure the backend is running, then run:

```bash
curl -X POST http://127.0.0.1:8000/reset
```

This copies `data/campus_customs.db` over `data/campus_customs_new.db` and records a reset event. Then use the React board to run tickets 101, 102, and 103 in order. Human approval is still required for any proposed payment or purchase.

## Build the frontend

```bash
cd frontend
npm run build
```

