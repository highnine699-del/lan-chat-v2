# LAN Chat V2 — Setup & Run

## Requirements
Python 3.10+ (3.12 recommended)

## Install dependencies
```
cd backend
pip install -r ../requirements.txt
```

## Run
Double-click `run.bat` — or from the project root:
```
cd backend
python -m uvicorn app:asgi_app --host 0.0.0.0 --port 8000
```

## Open
http://localhost:8000

## Environment variables (all optional)
| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Session signing key | Random per-run |
| `ADMIN_PASSWORD` | Enables server-admin login | Disabled |
| `SERVER_PASSWORD` | Requires password to join | Open |
| `PUBLIC_MODE` | Stricter limits, enforces SERVER_PASSWORD | false |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | * |
| `TURN_CREDENTIALS` | `user:pass` for TURN relay | STUN-only |
| `STATE_LOG` | Set to `1` for detailed state logging | Off |
| `DEBUG` | Verbose logging | Off |

## ngrok (optional — share across internet)
Set up via the launcher GUI (`launcher.py`).
