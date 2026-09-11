from __future__ import annotations
import asyncio, threading
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from .database import Database
from .obd_engine import OBDScanner
from .catalog import PARAMETERS
from .analytics import grade, health

app=FastAPI(title="AutoObserve",version="2.1.0")
db=Database(); scanner=None; current_vehicle=1; current_session=None; running=False

@app.get("/api/health")
def health_api(): return {"status":"ok","parameters":len(PARAMETERS),"connected":bool(scanner and scanner.connection and scanner.connection.is_connected())}
@app.get("/api/catalog")
def catalog(): return [{"key":p.key,"label":p.label,"unit":p.unit,"category":p.category,"source":p.source} for p in PARAMETERS]
@app.get("/api/vehicles")
def vehicles(): return db.vehicles()
@app.get("/api/vehicles/{vid}")
def vehicle(vid:int): return db.vehicle(vid) or {"error":"vehicle not found"}
@app.get("/api/vehicles/{vid}/telemetry")
def telemetry(vid:int,limit:int=500):
    return [dict(r) for r in db.conn.execute("SELECT * FROM telemetry WHERE vehicle_id=? ORDER BY id DESC LIMIT ?",(vid,limit)).fetchall()]
@app.get("/api/vehicles/{vid}/dtcs")
def dtcs(vid:int): return [dict(r) for r in db.conn.execute("SELECT * FROM dtcs WHERE vehicle_id=? ORDER BY id DESC",(vid,)).fetchall()]
@app.get("/api/vehicles/{vid}/health")
def vehicle_health(vid:int):
    rows=db.latest(vid); return health([{**x,"score":x.get("score")} for x in rows])

@app.post("/api/obd/connect")
def connect(port:str|None=None):
    global scanner,current_vehicle,current_session,running
    scanner=OBDScanner(port or None,fast=False,timeout=8)
    ok=scanner.connect()
    if not ok:return {"ok":False,"error":"Não foi possível conectar ao adaptador/ECU"}
    ident=scanner.identity(); vin=ident.get("vin")
    current_vehicle=db.find_or_create(vin=vin,name="Veículo identificado" if vin else "Veículo não identificado",make="Ford" if vin else "",model="")
    db.update_vehicle(current_vehicle,vin=vin,name=("Ford — VIN "+vin if vin else "Veículo não identificado"))
    current_session=db.start_session(current_vehicle,scanner.port_name,scanner.protocol,"ELM327/python-OBD")
    running=True
    return {"ok":True,"vehicle":db.vehicle(current_vehicle),"connection":ident}

@app.post("/api/obd/disconnect")
def disconnect():
    global running
    running=False
    if scanner:scanner.close()
    return {"ok":True}

@app.post("/api/diagnostics/read")
def read_diagnostics():
    if not scanner:return {"error":"scanner desconectado"}
    codes=scanner.dtcs()
    for item in codes:
        code=item[0] if isinstance(item,(tuple,list)) else str(item); db.save_dtc(current_vehicle,current_session,code)
    return {"dtcs":codes,"count":len(codes),"status":scanner.status()}

@app.post("/api/diagnostics/clear")
def clear_diagnostics():
    if not scanner:return {"error":"scanner desconectado"}
    return {"ok":scanner.clear_dtcs()}

@app.post("/api/diagnostics/freeze-frame")
def freeze_frame():
    if not scanner:return {"error":"scanner desconectado"}
    return {"data":scanner.freeze_frame()}

@app.get("/",response_class=HTMLResponse)
def home(): return HTML

@app.websocket("/ws/telemetry/{vid}")
async def ws(ws:WebSocket,vid:int):
    await ws.accept()
    while True:
        if running and scanner and scanner.connection and scanner.connection.is_connected():
            readings=scanner.read_all_supported()
            for x in readings:
                g=grade(x["key"],x["value"]); x.update(g); db.save_telemetry(vid,current_session,x["key"],x["value"],x["unit"],x["source"],g["status"],g["score"])
            await ws.send_json({"vehicle":db.vehicle(vid),"readings":readings,"health":health(readings)})
        else:
            await ws.send_json({"vehicle":db.vehicle(vid),"readings":[],"health":{"score":None,"status":"DESCONECTADO"}})
        await asyncio.sleep(1)

HTML='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoObserve</title><style>body{margin:0;font-family:system-ui;background:#f4f6f8;color:#17202a}header{background:#111827;color:#fff;padding:18px 5%;display:flex;justify-content:space-between}.wrap{max-width:1400px;margin:auto;padding:24px}.hero,.card,.table{background:#fff;border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 6px 24px #0001}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.v{font-size:30px;font-weight:800}.bar{height:10px;background:#e8edf0;border-radius:8px;overflow:hidden}.fill{height:100%;background:#19a957;width:0;transition:.4s}button{padding:11px 16px;border:0;border-radius:10px;background:#111827;color:white;font-weight:700;cursor:pointer;margin:4px}.muted{color:#66717e;font-size:13px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:13px}</style></head><body><header><strong>🚗 AUTO OBSERVE</strong><span id="status">🔴 Desconectado</span></header><main class="wrap"><section class="hero"><h2 id="vehicle">Veículo não identificado</h2><div id="meta" class="muted">Conecte o adaptador OBD</div><button onclick="connect()">🔌 Conectar</button><button onclick="disconnect()">Desconectar</button><button onclick="diag()">🔍 Ler erros</button><button onclick="clearDtc()">🗑 Limpar erros</button></section><section class="card"><h3>❤️ Saúde geral <span id="healthText">—</span></h3><div class="bar"><div id="healthBar" class="fill"></div></div></section><h3>Dados em tempo real</h3><section id="cards" class="grid"></section><section class="table"><h3>Todos os parâmetros respondidos</h3><table><thead><tr><th>Parâmetro</th><th>Valor</th><th>Unidade</th><th>Status</th><th>Score</th></tr></thead><tbody id="rows"></tbody></table></section></main><script>
let ws; async function connect(){let port=prompt('Porta serial (deixe vazio para autodetectar):','/dev/cu.usbserial-A77XUN0V');let r=await fetch('/api/obd/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({port:port||null})});let j=await r.json();if(!j.ok){alert(j.error);return} start(j.vehicle.id)} async function disconnect(){await fetch('/api/obd/disconnect',{method:'POST'});if(ws)ws.close();document.getElementById('status').textContent='🔴 Desconectado'} async function diag(){let r=await fetch('/api/diagnostics/read',{method:'POST'});let j=await r.json();alert(JSON.stringify(j,null,2))} async function clearDtc(){if(confirm('Confirma apagar os DTCs?')){let r=await fetch('/api/diagnostics/clear',{method:'POST'});alert(JSON.stringify(await r.json()))}} function start(id){ws=new WebSocket(`ws://${location.host}/ws/telemetry/${id}`);ws.onmessage=e=>{let j=JSON.parse(e.data);document.getElementById('status').textContent=j.readings.length?'🟢 Conectado':'🟡 Sem dados';let v=j.vehicle||{};document.getElementById('vehicle').textContent=v.name||'Veículo não identificado';document.getElementById('meta').textContent=`VIN: ${v.vin||'N/D'} • ${v.odometer?v.odometer+' km':'Odômetro N/D'}`;let h=j.health||{};document.getElementById('healthText').textContent=h.score==null?'—':`${h.score}/100 — ${h.status}`;document.getElementById('healthBar').style.width=(h.score||0)+'%';document.getElementById('cards').innerHTML=j.readings.slice(0,12).map(x=>`<div class="card"><div>${x.label}</div><div class="v">${x.value??'N/D'} ${x.unit||''}</div><div class="muted">${x.status} • ${x.score??'—'}/100</div><div class="bar"><div class="fill" style="width:${x.score||0}%"></div></div></div>`).join('');document.getElementById('rows').innerHTML=j.readings.map(x=>`<tr><td>${x.label}</td><td>${x.value??'N/D'}</td><td>${x.unit||''}</td><td>${x.status}</td><td>${x.score??'—'}</td></tr>`).join('')}} </script></body></html>'''
