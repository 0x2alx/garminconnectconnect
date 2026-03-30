---
name: full-system-check
description: Comprehensive read-only health check of the entire garminconnectconnect system — git, build, tests, services, logs
disable-model-invocation: true
---

# Full System Check — garminconnectconnect

## Project Context

- **Project path**: `/home/k2/CODE/garminconnectconnect`
- **Git remote**: `git@github.com:0x2alx/garminconnectconnect.git` (branch: `main`)
- **Language**: Python 3.12+ / SQLAlchemy 2.0 / FastMCP
- **Build**: `docker compose build --no-cache` (two-stage Dockerfile producing a wheel)
- **Unit tests**: `pytest tests/ --ignore=tests/test_integration.py -v`
- **Integration tests**: `pytest tests/test_integration.py -v` (requires running Docker containers)
- **Lint**: `ruff check src/ tests/`
- **Type check**: `mypy src/`
- **Docker Compose services**: `timescaledb` (pg16, port 5432), `mongodb` (mongo:7, port 27017), `garmin-server` (daemon), `garmin-mcp` (SSE on 127.0.0.1:8080), `garmin-cli` (profile: cli, not auto-started)
- **Container name prefix**: `garminconnectconnect-`
- **Log locations**: All services log to stdout — access via `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml logs <service>`
- **Databases**: TimescaleDB (PostgreSQL 16 + TimescaleDB extension, 34 tables, 8 hypertables), MongoDB 7 (`garmin_raw` database)
- **Report output**: `/home/k2/.openclaw/ext_ai_workdir/YYYY-MM-DD/claude_system_garmin-check_HHMM.md`

---

## Instructions

Run **4 Sonnet subagents in parallel** using the Agent tool. Each agent performs a read-only phase of the system check. After all 4 complete, compile their results into a single markdown report.

**CRITICAL**: Every agent must use `model: "sonnet"` and `subagent_type: "general-purpose"`.

### Phase 1: Git Hygiene

Launch an agent with this prompt:

```
You are performing a read-only git health check for the garminconnectconnect project.

Working directory: /home/k2/CODE/garminconnectconnect

Run these commands using the Bash tool (run independent ones in parallel):

1. `git -C /home/k2/CODE/garminconnectconnect status`
2. `git -C /home/k2/CODE/garminconnectconnect log --oneline -10`
3. `git -C /home/k2/CODE/garminconnectconnect stash list`
4. `git -C /home/k2/CODE/garminconnectconnect remote -v`
5. `git -C /home/k2/CODE/garminconnectconnect fetch origin --dry-run 2>&1`
6. `git -C /home/k2/CODE/garminconnectconnect rev-parse HEAD`
7. `git -C /home/k2/CODE/garminconnectconnect rev-parse --abbrev-ref HEAD`
8. `git -C /home/k2/CODE/garminconnectconnect diff --stat`
9. `git -C /home/k2/CODE/garminconnectconnect log origin/main..HEAD --oneline 2>/dev/null || echo "No tracking branch or no divergence"`
10. `git -C /home/k2/CODE/garminconnectconnect log HEAD..origin/main --oneline 2>/dev/null || echo "No tracking branch or no divergence"`

Return a structured report with these sections:
- **Branch**: current branch name
- **HEAD commit**: hash + message
- **Working tree**: clean or list of modified/untracked files
- **Stash**: number of stash entries, or "none"
- **Remote sync**: whether local is ahead/behind/diverged from origin/main, or in sync
- **Recent commits**: last 10 commits (oneline)
- **Status**: PASS (clean, in sync) / WARN (uncommitted changes or stash) / FAIL (diverged or broken remote)

DO NOT modify anything. Read-only.
```

### Phase 2: Build & Tests

Launch an agent with this prompt:

```
You are performing a read-only build and test check for the garminconnectconnect project.

Working directory: /home/k2/CODE/garminconnectconnect

Run these checks using the Bash tool. Run independent commands in parallel where possible.

**Step 1 — Lint check:**
Run: `cd /home/k2/CODE/garminconnectconnect && ruff check src/ tests/ 2>&1`
Parse the output: count errors/warnings, or confirm "All checks passed."

**Step 2 — Type check:**
Run: `cd /home/k2/CODE/garminconnectconnect && mypy src/ 2>&1`
Parse the output: count errors, or confirm clean.

**Step 3 — Unit tests:**
Run: `cd /home/k2/CODE/garminconnectconnect && python -m pytest tests/ --ignore=tests/test_integration.py -v --tb=short 2>&1`
Parse the output: extract total tests, passed, failed, errors, skipped counts from the summary line.
If there are failures, capture the first 3 failure names and their one-line error.

**Step 4 — Integration tests (conditional):**
First check if Docker is available and containers are running:
Run: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml ps --format '{{.Service}} {{.State}}' 2>&1`
If timescaledb and mongodb containers are running, run:
`cd /home/k2/CODE/garminconnectconnect && python -m pytest tests/test_integration.py -v --tb=short 2>&1`
If containers are not running, report: "Skipped (databases not running)"

**Step 5 — Package build check (dry run):**
Run: `cd /home/k2/CODE/garminconnectconnect && python -m build --no-isolation 2>&1 | tail -5`
This verifies the wheel can be built. If it fails, capture the error.

Return a structured report:
- **Lint**: PASS/FAIL + error count
- **Type check**: PASS/FAIL + error count
- **Unit tests**: X passed, Y failed, Z skipped (total N) — list failures if any
- **Integration tests**: X passed, Y failed, Z skipped OR "Skipped (reason)"
- **Package build**: PASS/FAIL
- **Overall status**: PASS (all green) / WARN (some skipped) / FAIL (any failures)

DO NOT modify anything. Read-only.
```

### Phase 3: Log Analysis (12 hours)

Launch an agent with this prompt:

```
You are performing a read-only log analysis for the garminconnectconnect project, checking the last 12 hours.

Working directory: /home/k2/CODE/garminconnectconnect
Docker compose file: /home/k2/CODE/garminconnectconnect/docker-compose.yml

Run these commands using the Bash tool (run all 4 in parallel):

1. **Daemon logs (garmin-server)**:
   `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml logs garmin-server --since 12h --no-log-prefix 2>&1 | tail -500`

2. **MCP server logs (garmin-mcp)**:
   `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml logs garmin-mcp --since 12h --no-log-prefix 2>&1 | tail -500`

3. **TimescaleDB logs**:
   `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml logs timescaledb --since 12h --no-log-prefix 2>&1 | tail -200`

4. **MongoDB logs**:
   `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml logs mongodb --since 12h --no-log-prefix 2>&1 | tail -200`

Analyze the logs for each service:

**For garmin-server (daemon):**
- Count sync cycles completed successfully
- Look for ERROR, Exception, Traceback, failed, 404, 429 (rate limit), 503, timeout
- Check if sync_cycle_complete events are appearing regularly (~every 10 minutes)
- Note any endpoints that are consistently failing
- Check last sync timestamp — how recent is it?

**For garmin-mcp:**
- Look for ERROR, Exception, Traceback, 500, 401 (auth failures)
- Count successful requests (202, 200 status codes)
- Note any unusual patterns

**For timescaledb:**
- Look for ERROR, FATAL, PANIC, deadlock, out of memory, connection refused
- Check for checkpoint warnings or replication issues
- Routine "checkpoint starting"/"checkpoint complete" messages are normal — skip those

**For mongodb:**
- Look for errors, authentication failures, connection issues
- Routine connection lifecycle events are normal — skip those

Return a structured report:
- **garmin-server**: status (HEALTHY/WARN/ERROR), sync cycles count, last sync time, issues found (if any)
- **garmin-mcp**: status, request count, issues found (if any)
- **timescaledb**: status, issues found (if any)
- **mongodb**: status, issues found (if any)
- **Top 3 issues** (if any): timestamp, service, description — ordered by severity
- **Overall status**: HEALTHY (no errors) / WARN (non-critical issues) / ERROR (critical failures)

Filter out routine noise. Only report genuinely concerning issues.

DO NOT modify anything. Read-only.
```

### Phase 4: Service & Connectivity Check

Launch an agent with this prompt:

```
You are performing a read-only service and connectivity check for the garminconnectconnect project.

Working directory: /home/k2/CODE/garminconnectconnect
Docker compose file: /home/k2/CODE/garminconnectconnect/docker-compose.yml

Run these commands using the Bash tool (run independent ones in parallel):

**Container status:**
1. `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml ps -a`
2. `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml ps --format '{{.Service}}\t{{.State}}\t{{.Health}}\t{{.RunningFor}}'`

**Database connectivity:**
3. TimescaleDB: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T timescaledb pg_isready -U garmin 2>&1`
4. TimescaleDB version: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T timescaledb psql -U garmin -d garmin -c "SELECT version(); SELECT extversion FROM pg_extension WHERE extname='timescaledb';" 2>&1`
5. TimescaleDB table count: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T timescaledb psql -U garmin -d garmin -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>&1`
6. MongoDB: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T mongodb mongosh --quiet --eval "db.adminCommand('ping')" 2>&1`
7. MongoDB collections: `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T mongodb mongosh --quiet garmin_raw --eval "db.getCollectionNames().length" 2>&1`

**MCP server:**
8. `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/sse 2>&1 || echo "UNREACHABLE"`
   (The MCP SSE endpoint should return 200 or similar on connection)

**Port checks:**
9. `ss -tlnp | grep -E ':(5432|8080|27017)' 2>&1 || echo "No matching ports found"`

**Image vs running version:**
10. Get the image ID of the running garmin-server container:
    `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml images garmin-server`
11. Get the latest built image:
    `docker images garminconnectconnect-garmin-server --format '{{.ID}} {{.CreatedAt}}' 2>&1`
12. Get the running container's start time:
    `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml ps garmin-server --format '{{.CreatedAt}}' 2>&1`

**Disk usage:**
13. `docker system df 2>&1`
14. `du -sh /home/k2/CODE/garminconnectconnect/ 2>&1`

**Data freshness (quick check):**
15. `docker compose -f /home/k2/CODE/garminconnectconnect/docker-compose.yml exec -T timescaledb psql -U garmin -d garmin -c "SELECT metric_name, MAX(date) AS last_date, COUNT(*) FILTER (WHERE status='completed') AS ok, COUNT(*) FILTER (WHERE status='failed') AS fail FROM sync_status GROUP BY metric_name ORDER BY metric_name;" 2>&1`

Return a structured report:
- **Containers**: list each service with state, health, uptime
- **TimescaleDB**: reachable (yes/no), version, table count, connection status
- **MongoDB**: reachable (yes/no), ping status, collection count
- **MCP server**: reachable (yes/no), HTTP status code
- **Ports**: which expected ports are listening (5432, 8080, 27017)
- **Image freshness**: whether running containers use the latest built images
- **Disk usage**: Docker system usage + project directory size
- **Data freshness**: last sync date per metric, any failures
- **Overall status**: PASS (all services up and healthy) / WARN (degraded) / FAIL (services down)

DO NOT modify anything. Read-only.
```

---

## After All Agents Complete

1. **Create the report directory** if it doesn't exist:
   ```
   mkdir -p /home/k2/.openclaw/ext_ai_workdir/$(date +%Y-%m-%d)
   ```

2. **Determine overall status**:
   - **HEALTHY**: All 4 phases report PASS/HEALTHY
   - **DEGRADED**: Any phase reports WARN but none report FAIL/ERROR
   - **CRITICAL**: Any phase reports FAIL/ERROR

3. **Write the report** to `/home/k2/.openclaw/ext_ai_workdir/YYYY-MM-DD/claude_system_garmin-check_HHMM.md` using this format:

   ```markdown
   # garminconnectconnect System Check — YYYY-MM-DD HH:MM

   **Overall Status**: [HEALTHY | DEGRADED | CRITICAL]

   ---

   ## Git Status
   [Paste Agent 1 results]

   ## Build & Tests
   [Paste Agent 2 results]

   ## Services & Connectivity
   [Paste Agent 4 results]

   ## Logs (12h)
   [Paste Agent 3 results]

   ## Skill Execution Issues
   [Note any agents that failed to run, timed out, or returned errors. "None" if all succeeded.]
   ```

4. **Conditional output**:
   - If **HEALTHY**: Print a single line:
     `✅ garminconnectconnect — HEALTHY | Build: ok | Tests: X/Y passed | Services: all up | 📄 <report-path>`
   - If **DEGRADED** or **CRITICAL**: Print 3-5 lines listing the issues with markers:
     - 🔴 for FAIL/ERROR/CRITICAL items
     - 🟡 for WARN/DEGRADED items
     - End with `📄 <report-path>`
