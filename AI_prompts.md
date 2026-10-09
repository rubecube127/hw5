# AI Prompts

## Problem 2: Study the Campus Customs Database

### Prompt

Open `data/campus.customs.db` and look through every table and its fields. Copy the original file to `data/campus_customs_new.db`; later problems will update that working copy. In the chat, list the important parts of the three open tickets so I can see how they relate to other tables.

Create `output/harness.md`. For each table, list the fields and one short line explaining why that table matters for the agents we will build.

### Follow-up prompt

If the named database file is empty or differs from the populated database in the folder, identify the discrepancy, use the populated source for the working copy, and clearly report which file was used.

## Problem 3: Build the MCP Server

### Prompt

Write an MCP server in `mcp_server/` using FastMCP. It will talk to `data/campus_customs_new.db`. You do not need to connect or run it right now. Every agent will eventually use the tools in this MCP server. For now, write three tools you think will be needed for tickets in the database. Keep the names clear. Do not fabricate any data; only use information from the database.

In `output/harness.md`, list each of the three MCP tools. For each tool, write which table it reads, which ticket it helps unlock (101, 102, or 103), and one sentence on why that tool is the right one for that ticket. Avoid vague lines like “reads inventory”; be as specific as possible while staying succinct. Tie the tool to the ticket in the explanation. Also add a short `mcp_server/README.md` file that explains what the MCP server is for, which database file it uses, and the three tools it has.

## Problem 4: Add the MCP Server to Vibe Coder + Test Each Tool

### Prompt

Add the Campus Customs MCP server to this project’s Codex MCP configuration. Inspect the existing configuration first, then register `mcp_server/server.py` as a local stdio MCP server using the project’s `.venv`. Use `data/campus_customs_new.db`, verify that the three tools are discoverable, and do not modify the database or run any tool against production data. Ask for approval before changing any user-level configuration outside this project. Save the connection JSON text in `.mcp.json` at the project root.

Test each of the three MCP tools and save evidence in `output/mcp_smoke.json`. For each tool, include a prompt that could be used to ask for the test, the tool name, and tool output that matches values in `data/campus_customs_new.db`.

## Problem 5: Build Agent Team + Grow MCP Tools

### Prompt

Using PydanticAI, build the Boss, Inventory, Accounting, Facilities, and Customer Service agents. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. Put one detailed prompt per agent in `backend/prompts/`, data types in `backend/models.py`, and agent files under `backend/`. Add any tools the agents need to the MCP server so they can work on the open tickets. Shop facts must come from the MCP server over `data/campus_customs_new.db`; do not invent a second shop-tools layer that bypasses MCP.

Wire the agents so they append to `output/audit_trail.json` as they run. For each agent-loop step, record enough to audit later. Append to this file; do not wipe it each run.

In `output/harness.md`, list each agent and each MCP tool, including tools added during this problem, with the table each tool uses. Add a succinct safety section covering real-business customer and money guardrails plus token-use limits. Update `mcp_server/README.md` so its tool list matches the current server.

## Problem 6: Plan the Three Tickets

### Prompt

Before wiring the backend, write down what we expect the team to do on each of the three open tickets. Build `output/desk_tickets.html`, a page I can double-click with one tab per ticket (101, 102, 103). Also add empty Cash and Reflection tabs for later problems.

On each ticket tab, fill an “Expected” section only, leaving room for an “Actual” section that will be filled later. For each ticket, write who Boss should call first and why, all expected agent delegations including specialist-to-specialist delegations, and the MCP tools expected to be used. Use only the handful of agents needed for each ticket; never call all agents. Do not run agents now; this is planning only.

## Problem 7: Backend Routes

### Prompt

In `backend/main.py`, use FastAPI to add routes that return the three tickets and their open/resolved status; take a ticket ID and run the agent team; return recent agent events including what each agent said and which tools they used; approve a payment or purchase only after explicit human approval, with the agent only preparing it; return the current checking balance; and reset the working database to the original values. Do not start the server or run agents yet.

## Problem 8: Agent Dashboard

### Prompt

Build the frontend dashboard in `frontend/` with React, Vite, and TypeScript. It must call the Problem 7 routes, show ticket state with red for open and green for resolved, run a selected ticket's agent team, show compact scrollable agent activity and summaries, support human payment/purchase approval, and show the checking balance after approval. Use a Yale-blue-and-white bulletin-board visual style.

## Problem 9: Resolve the Tickets

### Prompt

Reset `data/campus_customs_new.db`, record the starting checking balance, and run tickets 101, 102, and 103 to resolution with bounded token use. Update the Actual and Cash tabs in `output/desk_tickets.html` while preserving Expected content. Append real run events to `output/audit_trail.json`; save `output/resolved_tickets.json`; create `output/resolved_board.html` with a React-board screenshot for each resolved ticket; and complete `output/harness.md` with database, MCP, agents, routes, dashboard, and safety coverage.

## Problem 10: Reflection

### Prompt

In the Reflection tab, populate the supplied responses verbatim.
