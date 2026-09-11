from __future__ import annotations

RANGES={
 "coolant":(80,110), "iat":(-20,70), "battery":(12.0,15.0), "voltage":(12.0,15.0),
 "stft1":(-10,10), "ltft1":(-10,10), "stft2":(-10,10), "ltft2":(-10,10),
 "lambda_b1s1":(0.95,1.05), "load":(0,100), "throttle":(0,100), "fuel_level":(0,100)
}

def number(v):
    try:return float(v)
    except Exception:return None

def grade(key,value):
    v=number(value)
    if v is None:return {"score":None,"status":"N/D"}
    if key not in RANGES:return {"score":80,"status":"BOM"}
    lo,hi=RANGES[key]
    if lo<=v<=hi:return {"score":95,"status":"ÓTIMO"}
    margin=max((hi-lo)*0.25,1)
    if lo-margin<=v<=hi+margin:return {"score":65,"status":"ATENÇÃO"}
    return {"score":25,"status":"RUIM"}

def health(readings):
    scores=[x["score"] for x in readings if x.get("score") is not None]
    if not scores:return {"score":None,"status":"SEM DADOS"}
    s=round(sum(scores)/len(scores))
    status="ÓTIMO" if s>=90 else "BOM" if s>=75 else "ATENÇÃO" if s>=50 else "RUIM"
    return {"score":s,"status":status}
