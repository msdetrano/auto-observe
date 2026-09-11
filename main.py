from __future__ import annotations
import argparse, asyncio, json, sqlite3, threading, time
from datetime import datetime, timezone
from pathlib import Path

try:
    import obd
except ImportError:
    obd = None
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

DB = Path("data/autoobserve.db")
DB.parent.mkdir(exist_ok=True)

# 100+ parameter catalog. Availability is discovered at runtime; unsupported values are never faked.
CATALOG = [
("rpm","RPM","rpm","Engine"),("speed","Velocidade","km/h","Engine"),("load","Carga calculada","%","Engine"),("absolute_load","Carga absoluta","%","Engine"),("torque","Torque calculado","%","Engine"),("relative_torque","Torque relativo","%","Engine"),("runtime","Tempo ligado","s","Engine"),("start_time","Tempo desde partida","s","Engine"),("coolant","Temperatura arrefecimento","°C","Engine"),("oil_temp","Temperatura óleo","°C","Engine"),("iat","Temperatura admissão","°C","Air"),("ambient_temp","Temperatura ambiente","°C","Air"),("throttle","Posição borboleta","%","Air"),("pedal","Posição pedal","%","Air"),("tps_a","TPS A","%","Air"),("tps_b","TPS B","%","Air"),("tps_c","TPS C","%","Air"),("tps_d","TPS D","%","Air"),("tps_e","TPS E","%","Air"),("tps_f","TPS F","%","Air"),("map","MAP","kPa","Air"),("maf","MAF","g/s","Air"),("baro","BARO","kPa","Air"),("intake_pressure","Pressão admissão","kPa","Air"),("diff_pressure","Pressão diferencial","kPa","Air"),("egr","EGR","%","Emissions"),("egr_error","Erro EGR","%","Emissions"),("evap","EVAP","%","Emissions"),("purge","Purge EVAP","%","Emissions"),("boost","Pressão boost","kPa","Air"),("vacuum","Vácuo calculado","kPa","Air"),("stft1","STFT banco 1","%","Fuel"),("ltft1","LTFT banco 1","%","Fuel"),("stft2","STFT banco 2","%","Fuel"),("ltft2","LTFT banco 2","%","Fuel"),("fuel_level","Nível combustível","%","Fuel"),("fuel_rate","Taxa combustível","L/h","Fuel"),("fuel_pressure","Pressão combustível","kPa","Fuel"),("rail_pressure","Pressão fuel rail","kPa","Fuel"),("rail_abs","Pressão rail absoluta","kPa","Fuel"),("lambda","Lambda","λ","Fuel"),("equiv_ratio","Razão equivalência","λ","Fuel"),("afr","AFR estimado",":1","Calculated"),("commanded_afr","AFR comandado",":1","Fuel"),("ethanol","Etanol","%","Fuel"),("fuel_type","Tipo combustível","","Fuel"),("o2_b1s1","O2 B1S1","V","O2"),("o2_b1s2","O2 B1S2","V","O2"),("o2_b2s1","O2 B2S1","V","O2"),("o2_b2s2","O2 B2S2","V","O2"),("o2_stft_b1","O2 STFT B1","%","O2"),("o2_stft_b2","O2 STFT B2","%","O2"),("o2_sensor_b1","O2 sensor B1","V","O2"),("o2_sensor_b2","O2 sensor B2","V","O2"),("o2_heater","Aquecimento O2","%","O2"),("catalyst_temp","Temperatura catalisador","°C","Emissions"),("catalyst_monitor","Monitor catalisador","","Emissions"),("battery","Tensão bateria","V","Electrical"),("ecu_voltage","Tensão ECU","V","Electrical"),("charging_voltage","Tensão carga","V","Electrical"),("battery_temp","Temperatura bateria","°C","Electrical"),("battery_current","Corrente bateria","A","Electrical"),("alternator","Alternador","%","Electrical"),("trans_temp","Temperatura transmissão","°C","Transmission"),("trans_input_rpm","RPM entrada transmissão","rpm","Transmission"),("trans_output_rpm","RPM saída transmissão","rpm","Transmission"),("trans_input_speed","Velocidade entrada","km/h","Transmission"),("trans_output_speed","Velocidade saída","km/h","Transmission"),("gear","Marcha","","Transmission"),("selector","Seletor","","Transmission"),("converter_torque","Torque conversor","%","Transmission"),("converter_slip","Slip conversor","rpm","Transmission"),("vin","VIN / Chassi","","Identity"),("calibration_id","Calibration ID","","Identity"),("cvn","CVN","","Identity"),("ecu_name","Nome ECU","","Identity"),("ecu_version","Versão ECU","","Identity"),("protocol","Protocolo OBD","","Connection"),("can_status","Status CAN","","Connection"),("distance_dtc","Distância desde DTC","km","Diagnostics"),("time_dtc","Tempo desde DTC","min","Diagnostics"),("mil","MIL","","Diagnostics"),("dtc_confirmed","DTC confirmado","count","Diagnostics"),("dtc_pending","DTC pendente","count","Diagnostics"),("dtc_permanent","DTC permanente","count","Diagnostics"),("freeze_frame","Freeze Frame","","Diagnostics"),("readiness_misfire","Readiness misfire","","Readiness"),("readiness_fuel","Readiness fuel system","","Readiness"),("readiness_components","Readiness components","","Readiness"),("readiness_catalyst","Readiness catalyst","","Readiness"),("readiness_heated_catalyst","Readiness heated catalyst","","Readiness"),("readiness_evap","Readiness EVAP","","Readiness"),("readiness_secondary_air","Readiness secondary air","","Readiness"),("readiness_o2","Readiness O2","","Readiness"),("readiness_o2_heater","Readiness O2 heater","","Readiness"),("readiness_egr","Readiness EGR","","Readiness"),("odometer","Odômetro","km","Vehicle"),("session_distance","Distância sessão","km","Vehicle"),("trip_distance","Distância viagem","km","Trip"),("max_speed","Velocidade máxima","km/h","Trip"),("max_rpm","RPM máxima","rpm","Trip"),("idle_time","Tempo marcha lenta","s","Trip"),("drive_time","Tempo dirigindo","s","Trip"),("fuel_used","Combustível consumido","L","Trip"),("avg_consumption","Consumo médio","km/L","Trip"),("instant_consumption","Consumo instantâneo","km/L","Trip"),("autonomy","Autonomia estimada","km","Trip"),("volumetric_efficiency","Eficiência volumétrica","%","Calculated"),("thermal_load","Carga térmica","%","Calculated"),("idle_stability","Estabilidade lenta","%","Calculated"),("voltage_stability","Estabilidade tensão","%","Calculated"),("fuel_trim_health","Saúde fuel trim","/100","Calculated"),("engine_health","Saúde motor","/100","Calculated"),("electrical_health","Saúde elétrica","/100","Calculated"),("emissions_health","Saúde emissões","/100","Calculated"),("sensor_health","Saúde sensores","/100","Calculated"),("overall_health","Saúde geral","/100","Calculated"),("anomaly_score","Score anomalia","/100","Calculated"),("degradation_trend","Tendência degradação","%","Calculated"),("ecu_response","Resposta ECU","ms","Connection"),("sample_rate","Taxa amostragem","Hz","Connection"),("adapter","Adaptador","","Connection"),("module_count","Módulos encontrados","count","Diagnostics"),("pcm_status","PCM","","Modules"),("ipc_status","IPC","","Modules"),("bcm_status","BCM","","Modules"),("abs_status","ABS","","Modules"),("rcm_status","RCM","","Modules"),("tcm_status","TCM","","Modules"),("hvac_status","HVAC","","Modules"),("apim_status","APIM","","Modules"),("acm_status","ACM","","Modules"),
]

app = FastAPI(title="AutoObserve", version="2.0.0")
conn = None
lock = threading.Lock()
vehicle_id = 1


def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY, vin TEXT, name TEXT, make TEXT, model TEXT, year INTEGER, engine TEXT, fuel TEXT, odometer REAL, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, ts TEXT, key TEXT, value REAL, unit TEXT, source TEXT, status TEXT, score INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, started_at TEXT, ended_at TEXT, port TEXT, protocol TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS dtcs (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, ts TEXT, code TEXT, module TEXT, state TEXT, description TEXT)")
    c.commit(); return c

conn = db()
if conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 0:
    conn.execute("INSERT INTO vehicles (name,make,model,year,engine,fuel,created_at) VALUES (?,?,?,?,?,?,?)", ("Veículo não identificado","","",None,"","",datetime.now(timezone.utc).isoformat()))
    conn.commit()


def grade(key, value):
    if value is None: return (None, "UNSUPPORTED")
    try: v = float(value)
    except Exception: return (None, "REAL_ECU")
    # Conservative generic ranges; not a manufacturer-specific diagnosis.
    ranges = {"coolant":(80,110),"iat":(-20,70),"battery":(12.0,15.0),"ecu_voltage":(12.0,15.0),"stft1":(-10,10),"ltft1":(-10,10),"load":(0,100),"throttle":(0,100),"fuel_level":(0,100),"lambda":(0.95,1.05)}
    lo,hi=ranges.get(key,(None,None))
    if lo is None: return (80,"REAL_ECU")
    if lo <= v <= hi: return (95,"REAL_ECU")
    margin=max((hi-lo)*0.25,1)
    if lo-margin <= v <= hi+margin: return (65,"REAL_ECU")
    return (25,"REAL_ECU")


def latest_rows():
    rows=conn.execute("SELECT key,value,unit,source,status,score,MAX(ts) ts FROM telemetry WHERE vehicle_id=? GROUP BY key",(vehicle_id,)).fetchall()
    return [dict(r) for r in rows]


def vehicle():
    r=conn.execute("SELECT * FROM vehicles WHERE id=?",(vehicle_id,)).fetchone(); return dict(r)

@app.get("/api/health")
def api_health(): return {"status":"ok","service":"AutoObserve","catalog_parameters":len(CATALOG)}

@app.get("/api/catalog")
def api_catalog(): return [{"key":k,"name":n,"unit":u,"category":c} for k,n,u,c in CATALOG]

@app.get("/api/vehicles")
def api_vehicles(): return [dict(r) for r in conn.execute("SELECT * FROM vehicles ORDER BY id").fetchall()]

@app.get("/api/vehicles/{vid}")
def api_vehicle(vid:int):
    r=conn.execute("SELECT * FROM vehicles WHERE id=?",(vid,)).fetchone(); return dict(r) if r else {"error":"vehicle not found"}

@app.get("/api/vehicles/{vid}/telemetry")
def api_telemetry(vid:int, limit:int=500):
    return [dict(r) for r in conn.execute("SELECT * FROM telemetry WHERE vehicle_id=? ORDER BY id DESC LIMIT ?",(vid,limit)).fetchall()]

@app.get("/api/vehicles/{vid}/dtcs")
def api_dtcs(vid:int): return [dict(r) for r in conn.execute("SELECT * FROM dtcs WHERE vehicle_id=? ORDER BY id DESC",(vid,)).fetchall()]

@app.get("/api/vehicles/{vid}/health")
def api_vehicle_health(vid:int):
    rows=conn.execute("SELECT score FROM telemetry WHERE vehicle_id=? AND score IS NOT NULL ORDER BY id DESC LIMIT 500",(vid,)).fetchall(); scores=[r[0] for r in rows]
    return {"score":round(sum(scores)/len(scores)) if scores else None,"status":"EXCELENTE" if scores and sum(scores)/len(scores)>=90 else "SEM DADOS" if not scores else "ATENÇÃO"}

@app.get("/api/vehicles/{vid}/report")
def api_report(vid:int):
    v=api_vehicle(vid); data=[x for x in latest_rows() if True] if vid==vehicle_id else []
    return {"vehicle":v,"catalog_count":len(CATALOG),"telemetry":data,"dtcs":api_dtcs(vid),"health":api_vehicle_health(vid)}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(HTML)

@app.websocket("/ws/telemetry/{vid}")
async def websocket_telemetry(ws:WebSocket,vid:int):
    await ws.accept()
    while True:
        await ws.send_json({"timestamp":datetime.now(timezone.utc).isoformat(),"vehicle":api_vehicle(vid),"telemetry":latest_rows() if vid==vehicle_id else [],"health":api_vehicle_health(vid)})
        await asyncio.sleep(1)

HTML = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoObserve</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui;background:#f4f6f8;color:#18212b}header{background:#111827;color:white;padding:18px 28px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:2}header h1{margin:0;font-size:22px}header small{opacity:.7}.wrap{max-width:1500px;margin:auto;padding:24px}.hero{background:white;border-radius:18px;padding:22px;box-shadow:0 8px 30px #0000000d;margin-bottom:20px}.hero h2{margin:0 0 5px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.card{background:white;border-radius:16px;padding:18px;box-shadow:0 5px 22px #0000000a}.value{font-size:30px;font-weight:750;margin:7px 0}.muted{color:#687585;font-size:13px}.bar{height:10px;background:#e8edf1;border-radius:10px;overflow:hidden;margin-top:10px}.fill{height:100%;width:0;background:#18a957;transition:width .4s}.section{margin:24px 0 10px;font-size:18px;font-weight:700}.pill{display:inline-block;border-radius:999px;padding:5px 9px;font-size:12px;font-weight:700;background:#e8f7ee;color:#087b3e}.table{background:white;border-radius:16px;overflow:auto;box-shadow:0 5px 22px #0000000a}.table table{width:100%;border-collapse:collapse}.table th,.table td{padding:11px 14px;border-bottom:1px solid #edf0f2;text-align:left;font-size:13px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-top:15px}button{border:0;border-radius:10px;padding:11px 16px;font-weight:700;cursor:pointer;background:#111827;color:white}button.secondary{background:#e9edf1;color:#18212b}@media(max-width:650px){.wrap{padding:12px}header{padding:15px}.value{font-size:25px}}
</style></head><body><header><h1>🚗 AutoObserve</h1><div id="conn">🔴 desconectado</div></header><main class="wrap"><section class="hero"><h2 id="vehicle">Veículo não identificado</h2><div class="muted" id="identity">Conecte o OBD para identificar VIN, ECU e protocolo.</div><div class="toolbar"><button onclick="load()">🔄 Atualizar</button><button class="secondary" onclick="location.href='/docs'">🌐 API / Swagger</button></div></section><div class="grid"><div class="card"><div class="muted">Saúde geral</div><div class="value" id="health">N/D</div><div class="bar"><div class="fill" id="healthbar"></div></div></div><div class="card"><div class="muted">RPM</div><div class="value" id="rpm">N/D</div><div class="pill" id="rpmst">aguardando</div></div><div class="card"><div class="muted">Temperatura</div><div class="value" id="coolant">N/D</div><div class="pill">referência contextual</div></div><div class="card"><div class="muted">Combustível</div><div class="value" id="fuel">N/D</div><div class="pill">ECU quando suportado</div></div></div><div class="section">📊 Dados disponíveis</div><div class="table"><table><thead><tr><th>Parâmetro</th><th>Valor</th><th>Unidade</th><th>Origem</th><th>Status</th><th>Score</th></tr></thead><tbody id="rows"></tbody></table></div><div class="section">🧠 O que significa?</div><section class="hero"><p>O AutoObserve separa leitura real da ECU, leitura de módulo, cálculo e estimativa. A faixa de referência é apenas orientação: valores corretos dependem do motor, temperatura, carga e estratégia da ECU.</p><p><b>Mais de 100 parâmetros</b> ficam disponíveis no catálogo. O carro só será considerado compatível com aqueles que realmente responderem.</p></section></main><script>
const fmt=x=>x==null?'N/D':(typeof x==='number'?Number(x.toFixed(2)):x);function scoreText(s){if(s==null)return 'N/D';if(s>=90)return '🟢 EXCELENTE';if(s>=75)return '🔵 BOM';if(s>=50)return '🟡 ATENÇÃO';if(s>=30)return '🟠 RUIM';return '🔴 CRÍTICO'}function render(d){const v=d.vehicle||{};document.getElementById('vehicle').textContent=[v.make,v.model,v.engine,v.year].filter(Boolean).join(' ')||v.name||'Veículo não identificado';document.getElementById('identity').textContent=`VIN: ${v.vin||'N/D'}  •  Odômetro: ${v.odometer??'N/D'} km`;document.getElementById('conn').textContent='🟢 dados atualizados';const h=d.health?.score;document.getElementById('health').textContent=h==null?'N/D':`${h}/100 ${scoreText(h)}`;document.getElementById('healthbar').style.width=(h||0)+'%';const m={};(d.telemetry||[]).forEach(x=>m[x.key]=x);document.getElementById('rpm').textContent=m.rpm?fmt(m.rpm.value)+' rpm':'N/D';document.getElementById('coolant').textContent=m.coolant?fmt(m.coolant.value)+' °C':'N/D';document.getElementById('fuel').textContent=m.fuel_level?fmt(m.fuel_level.value)+' %':'N/D';document.getElementById('rows').innerHTML=(d.telemetry||[]).map(x=>`<tr><td>${x.key}</td><td>${fmt(x.value)}</td><td>${x.unit||''}</td><td>${x.source||''}</td><td>${x.status||''} ${scoreText(x.score)}</td><td>${x.score??'N/D'}</td></tr>`).join('')}async function load(){const r=await fetch('/api/vehicles/1/report');render(await r.json())}load();const ws=new WebSocket(`ws://${location.host}/ws/telemetry/1`);ws.onmessage=e=>render(JSON.parse(e.data));
</script></body></html>'''

def connect(port=None):
    if obd is None: raise RuntimeError('python-OBD não instalado')
    return obd.OBD(portstr=port, fast=False, timeout=2)

def scan(port=None):
    c=connect(port); print('AUTO OBSERVE — FULL VEHICLE REPORT'); print('Status:',c.status()); print('Porta:',port or 'auto'); print('Catálogo:',len(CATALOG),'parâmetros')
    for key,name,unit,cat in CATALOG:
        # The catalog is intentionally broader than generic python-OBD. Actual command mapping is added only when supported.
        print(f'{name:<30} N/D  {unit:<8} [UNSUPPORTED/NOT MAPPED]')
    c.close()

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd')
    w=sub.add_parser('web'); w.add_argument('--host',default='127.0.0.1'); w.add_argument('--port',type=int,default=8000)
    s=sub.add_parser('scan'); s.add_argument('--port'); l=sub.add_parser('live'); l.add_argument('--port')
    a=p.parse_args()
    if a.cmd=='web':
        import uvicorn; uvicorn.run(app,host=a.host,port=a.port)
    elif a.cmd=='scan': scan(a.port)
    elif a.cmd=='live':
        c=connect(a.port)
        try:
            while True: print(datetime.now().strftime('%H:%M:%S'),'connected:',c.status()); time.sleep(1)
        finally: c.close()
    else: p.print_help()
if __name__=='__main__': main()
