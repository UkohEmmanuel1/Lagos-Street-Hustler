import asyncio
import json
import os
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from passlib.context import CryptContext

APP_NAME = "Lagos Street Hustler API"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(48)
    # Configure JWT_SECRET_KEY in production to keep tokens valid across restarts.
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "10080"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = os.getenv("SQLITE_PATH", "/tmp/lagos_street_hustler.db")
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

app = FastAPI(title=APP_NAME, version="2.0.0")
allowed_origins = [v.strip() for v in os.getenv("CORS_ORIGINS", "*").split(",") if v.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

MISSIONS = [
    {"id": "first-day", "title": "First Day in Lagos", "description": "Find your first street contact.", "reward": "2500", "xp": 100},
    {"id": "food-run", "title": "Food Delivery", "description": "Deliver a food order before traffic wins.", "reward": "15000", "xp": 250},
    {"id": "industrial", "title": "Industrial Delivery", "description": "Take the logistics contract to the refinery district.", "reward": "2500000", "xp": 1200},
]

def connect_db():
    # SQLite is a simple local fallback. For durable production persistence, configure DATABASE_URL.
    if DATABASE_URL.startswith("postgres"):
        try:
            import psycopg
            from psycopg.rows import dict_row
            conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
            conn.execute("CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS messages (id BIGSERIAL PRIMARY KEY, room TEXT NOT NULL, sender TEXT NOT NULL, body TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL)")
            return conn, True
        except Exception as exc:
            raise RuntimeError("PostgreSQL connection failed; check DATABASE_URL and database network access.") from exc
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at REAL NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT NOT NULL, sender TEXT NOT NULL, body TEXT NOT NULL, created_at REAL NOT NULL)")
    conn.commit()
    return conn, False

def init_db():
    conn, pg = connect_db()
    conn.close()
init_db()

def db_one(sql: str, params: tuple = ()):
    conn, pg = connect_db()
    try:
        cur = conn.execute(sql.replace("?", "%s") if pg else sql, params)
        row = cur.fetchone()
        if row is None: return None
        return dict(row) if not pg else row
    finally:
        conn.close()

def db_run(sql: str, params: tuple = ()):
    conn, pg = connect_db()
    try:
        conn.execute(sql.replace("?", "%s") if pg else sql, params)
        if not pg: conn.commit()
    finally:
        conn.close()

def create_token(player_id: str, username: str):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": player_id, "username": username, "iat": now,
                       "exp": now + timedelta(minutes=TOKEN_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM)

def token_player(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub") or not payload.get("username"): raise ValueError()
        return {"id": payload["sub"], "username": payload["username"]}
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

def current_player(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(status_code=401, detail="Bearer access token required")
    return token_player(credentials.credentials)

class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=10, max_length=128)

class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=1, max_length=128)

class MessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    recipient: str | None = Field(default=None, max_length=24)
    group: str | None = Field(default=None, min_length=1, max_length=64)

class PositionInput(BaseModel):
    x: float = Field(ge=-100, le=100)
    z: float = Field(ge=-100, le=100)

@app.get("/health")
def health():
    return {"status": "ok", "service": "lagos-street-hustler-api", "version": "2.0.0"}

@app.get("/missions")
def missions():
    return MISSIONS

@app.get("/players/me")
def player(me: dict = Depends(current_player)):
    return {"id": me["id"], "name": me["username"], "level": 1, "xp": 0, "reputation": 0,
            "money": {"balance": "2500000", "currency": "NGN"}}

@app.post("/auth/register", status_code=201)
def register(data: RegisterInput):
    username = data.username.lower()
    player_id = secrets.token_urlsafe(16)
    try:
        db_run("INSERT INTO players(id, username, password_hash, created_at) VALUES(?,?,?,?)",
               (player_id, username, pwd_context.hash(data.password), time.time()))
    except Exception:
        raise HTTPException(status_code=409, detail="Username is already taken")
    return {"access_token": create_token(player_id, username), "token_type": "bearer",
            "player": {"id": player_id, "username": username}}

@app.post("/auth/login")
def login(data: LoginInput):
    row = db_one("SELECT id, username, password_hash FROM players WHERE username = ?", (data.username.lower(),))
    if not row or not pwd_context.verify(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_token(row["id"], row["username"]), "token_type": "bearer",
            "player": {"id": row["id"], "username": row["username"]}}

@app.get("/players")
def players(me: dict = Depends(current_player)):
    conn, pg = connect_db()
    try:
        rows = conn.execute("SELECT id, username FROM players ORDER BY username LIMIT 100").fetchall()
        return {"players": [dict(r) for r in rows]}
    finally:
        conn.close()

@app.get("/messages")
def get_messages(room: str = Query("nearby", min_length=1, max_length=80),
                 limit: int = Query(50, ge=1, le=100), me: dict = Depends(current_player)):
    if room.startswith("dm:") and me["id"] not in room.split(":")[1:]:
        raise HTTPException(status_code=403, detail="Not a member of this conversation")
    if room.startswith("group:") and me["id"] not in rooms.get(room, set()):
        raise HTTPException(status_code=403, detail="Join this group before reading its messages")
    conn, pg = connect_db()
    try:
        sql = "SELECT id, room, sender, body, created_at FROM messages WHERE room = ? ORDER BY id DESC LIMIT ?"
        rows = conn.execute(sql.replace("?", "%s") if pg else sql, (room, limit)).fetchall()
        return {"messages": [dict(r) for r in reversed(rows)]}
    finally:
        conn.close()

@app.post("/missions/{mission_id}/complete")
def complete(mission_id: str, me: dict = Depends(current_player)):
    mission = next((m for m in MISSIONS if m["id"] == mission_id), None)
    if not mission: raise HTTPException(status_code=404, detail="Mission not found")
    # This endpoint returns mission metadata only; authoritative wallet rewards require a persisted game-state ledger.
    return {"mission": mission, "reward": mission["reward"], "status": "accepted"}

@app.get("/apps")
def phone_apps(me: dict = Depends(current_player)):
    return {"apps": [
        {"id":"map","name":"Map / GPS","status":"available"},
        {"id":"wallet","name":"Bank & wallet","status":"prototype"},
        {"id":"contacts","name":"Contacts","status":"available"},
        {"id":"social","name":"Social feed","status":"prototype"},
        {"id":"rides","name":"Ride-hailing","status":"prototype"},
        {"id":"jobs","name":"Jobs & business","status":"prototype"},
        {"id":"chat","name":"Messages","status":"available"},
        {"id":"voice","name":"Voice chat","status":"webrtc-signalling"},
    ]}

# Process-local connections/presence are suitable for a single API instance.
# Use Redis pub/sub and a shared presence store before scaling to multiple instances.
connections: dict[str, set[WebSocket]] = defaultdict(set)
positions: dict[str, dict[str, Any]] = {}
rooms: dict[str, set[str]] = defaultdict(set)
connection_lock = asyncio.Lock()

async def send_json_safe(ws: WebSocket, payload: dict):
    try: await ws.send_json(payload)
    except Exception: pass

async def broadcast(room: str, payload: dict, exclude: WebSocket | None = None):
    targets = []
    async with connection_lock:
        for player_id in rooms.get(room, set()):
            for ws in connections.get(player_id, set()):
                if ws is not exclude: targets.append(ws)
    await asyncio.gather(*(send_json_safe(ws, payload) for ws in targets), return_exceptions=True)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(..., min_length=10)):
    try:
        me = token_player(token)
    except HTTPException:
        await ws.close(code=4401, reason="Unauthorized")
        return
    await ws.accept()
    pid = me["id"]
    async with connection_lock:
        connections[pid].add(ws)
        rooms["nearby"].add(pid)
        positions.setdefault(pid, {"id": pid, "username": me["username"], "x": 0, "z": 0})
    await broadcast("nearby", {"type":"presence","event":"online","player":{"id":pid,"username":me["username"]}}, exclude=ws)
    recent_messages = deque()
    try:
        await ws.send_json({"type":"ready","player":{"id":pid,"username":me["username"]}})
        while True:
            data = await ws.receive_json()
            if not isinstance(data, dict): continue
            kind = data.get("type")
            if kind == "position":
                try:
                    x, z = float(data["x"]), float(data["z"])
                    if not (-100 <= x <= 100 and -100 <= z <= 100): continue
                except (KeyError, TypeError, ValueError): continue
                positions[pid] = {"id":pid,"username":me["username"],"x":x,"z":z}
                nearby = [p for other, p in positions.items() if other != pid and (p["x"]-x)**2 + (p["z"]-z)**2 <= 900]
                await ws.send_json({"type":"nearby_players","players":nearby})
                await broadcast("nearby", {"type":"player_moved","player":positions[pid]}, exclude=ws)
            elif kind == "join_group":
                group = str(data.get("group", ""))[:48]
                if not group or not all(c.isalnum() or c in "-_" for c in group): continue
                room = "group:" + group
                async with connection_lock: rooms[room].add(pid)
                await ws.send_json({"type":"joined_group","group":group})
            elif kind == "message":
                now = time.monotonic()
                while recent_messages and now - recent_messages[0] > 5:
                    recent_messages.popleft()
                if len(recent_messages) >= 5:
                    await ws.send_json({"type":"error","message":"Chat rate limit: wait a few seconds before sending again"})
                    continue
                body = str(data.get("body", "")).strip()
                if not body or len(body) > 1000: continue
                recent_messages.append(now)
                recipient = data.get("recipient")
                group = data.get("group")
                if recipient:
                    row = db_one("SELECT id FROM players WHERE username = ?", (str(recipient).lower(),))
                    if not row: await ws.send_json({"type":"error","message":"Player not found"}); continue
                    # Stable, non-guessable room IDs based on player IDs, not user-supplied room names.
                    a, b = sorted([pid, row["id"]])
                    room = "dm:" + a + ":" + b
                    allowed = {pid, row["id"]}
                    for member in allowed: rooms[room].add(member)
                elif group:
                    room = "group:" + str(group)[:48]
                    if pid not in rooms.get(room, set()):
                        await ws.send_json({"type":"error","message":"Join this group before messaging"}); continue
                else:
                    room = "nearby"
                msg = {"type":"message","room":room,"sender":me["username"],"body":body,"created_at":time.time()}
                db_run("INSERT INTO messages(room, sender, body, created_at) VALUES(?,?,?,?)", (room, me["username"], body, msg["created_at"]))
                await broadcast(room, msg, exclude=ws if room == "nearby" else None)
                if room == "nearby": await send_json_safe(ws, msg)
            elif kind == "voice_signal":
                target = str(data.get("to", ""))[:24].lower()
                signal = data.get("signal")
                if not target or not isinstance(signal, dict): continue
                row = db_one("SELECT id FROM players WHERE username = ?", (target,))
                if row:
                    for target_ws in list(connections.get(row["id"], set())):
                        await send_json_safe(target_ws, {"type":"voice_signal","from":me["username"],"signal":signal})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with connection_lock:
            connections[pid].discard(ws)
            if not connections[pid]:
                connections.pop(pid, None)
                positions.pop(pid, None)
                for room_members in rooms.values(): room_members.discard(pid)
        await broadcast("nearby", {"type":"presence","event":"offline","player":{"id":pid,"username":me["username"]}}, exclude=ws)
