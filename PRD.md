# PRD: FRED Web Dashboard

## Objective
Create a simple web dashboard showing agent status, recent trades, and performance.

## Requirements
- [ ] FastAPI backend with /api/status, /api/trades, /api/metrics endpoints
- [ ] Simple HTML/JS frontend (single index.html with inline JS)
- [ ] Show: wallet balance, recent trades, P&L chart
- [ ] Auto-refresh every 30 seconds
- [ ] Add `--dashboard` flag to main.py to serve on port 8080

## Validation Checklist
- [ ] `python main.py --dashboard` starts server
- [ ] http://localhost:8080 loads dashboard
- [ ] API endpoints return JSON

## Files to Create/Modify
- `dashboard.py` — FastAPI app
- `static/index.html` — dashboard frontend
- `main.py` — add --dashboard flag
- `requirements.txt` — add fastapi, uvicorn

## Out of Scope
- Authentication
- Persistent database
