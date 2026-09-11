from pathlib import Path
import sqlite3
from datetime import datetime, timezone

DB_PATH = Path("data/autoobserve.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = '''
CREATE TABLE IF NOT EXISTS vehicles (
 id INTEGER PRIMARY KEY AUTOINCREMENT, vin TEXT, name TEXT NOT NULL, make TEXT, model TEXT,
 year INTEGER, engine TEXT, fuel TEXT, odometer REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER NOT NULL, started_at TEXT NOT NULL,
 ended_at TEXT, port TEXT, protocol TEXT, adapter TEXT, FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);
CREATE TABLE IF NOT EXISTS telemetry (
 id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER NOT NULL, session_id INTEGER,
 ts TEXT NOT NULL, key TEXT NOT NULL, value TEXT, unit TEXT, source TEXT, status TEXT, score INTEGER,
 FOREIGN KEY(vehicle_id) REFERENCES vehicles(id), FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS dtcs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER NOT NULL, session_id INTEGER, ts TEXT NOT NULL,
 code TEXT, module TEXT, state TEXT, description TEXT, FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_key_ts ON telemetry(vehicle_id,key,ts);
CREATE INDEX IF NOT EXISTS idx_dtcs_vehicle_ts ON dtcs(vehicle_id,ts);
'''

def now(): return datetime.now(timezone.utc).isoformat()

class Database:
    def __init__(self, path=DB_PATH):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path,check_same_thread=False)
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript(SCHEMA); self.conn.commit()

    def vehicle(self, vehicle_id):
        r=self.conn.execute("SELECT * FROM vehicles WHERE id=?",(vehicle_id,)).fetchone()
        return dict(r) if r else None

    def vehicles(self): return [dict(r) for r in self.conn.execute("SELECT * FROM vehicles ORDER BY id")]

    def find_or_create(self, vin=None, name="Veículo não identificado", make="", model="", year=None):
        if vin:
            r=self.conn.execute("SELECT * FROM vehicles WHERE vin=?",(vin,)).fetchone()
            if r: return r["id"]
        t=now(); cur=self.conn.execute("INSERT INTO vehicles(vin,name,make,model,year,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(vin,name,make,model,year,t,t)); self.conn.commit(); return cur.lastrowid

    def update_vehicle(self, vehicle_id, **fields):
        allowed={k:v for k,v in fields.items() if k in {"vin","name","make","model","year","engine","fuel","odometer"}}
        if not allowed:return
        allowed["updated_at"]=now(); sets=", ".join(f"{k}=?" for k in allowed); self.conn.execute(f"UPDATE vehicles SET {sets} WHERE id=?",(*allowed.values(),vehicle_id)); self.conn.commit()

    def start_session(self, vehicle_id, port="", protocol="", adapter=""):
        cur=self.conn.execute("INSERT INTO sessions(vehicle_id,started_at,port,protocol,adapter) VALUES(?,?,?,?,?)",(vehicle_id,now(),port,protocol,adapter)); self.conn.commit(); return cur.lastrowid

    def end_session(self, session_id): self.conn.execute("UPDATE sessions SET ended_at=? WHERE id=?",(now(),session_id)); self.conn.commit()

    def save_telemetry(self, vehicle_id, session_id, key, value, unit="", source="REAL_ECU", status="AVAILABLE", score=None):
        self.conn.execute("INSERT INTO telemetry(vehicle_id,session_id,ts,key,value,unit,source,status,score) VALUES(?,?,?,?,?,?,?,?,?)",(vehicle_id,session_id,now(),key,None if value is None else str(value),unit,source,status,score)); self.conn.commit()

    def save_dtc(self, vehicle_id, session_id, code, module="OBD", state="CONFIRMED", description=""):
        self.conn.execute("INSERT INTO dtcs(vehicle_id,session_id,ts,code,module,state,description) VALUES(?,?,?,?,?,?,?)",(vehicle_id,session_id,now(),code,module,state,description)); self.conn.commit()

    def latest(self, vehicle_id):
        rows=self.conn.execute('''SELECT t.* FROM telemetry t JOIN (SELECT key,MAX(id) id FROM telemetry WHERE vehicle_id=? GROUP BY key) x ON x.id=t.id ORDER BY t.key''',(vehicle_id,)).fetchall(); return [dict(r) for r in rows]
