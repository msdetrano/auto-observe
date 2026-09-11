from __future__ import annotations
import time
from typing import Any

try:
    import obd
except ImportError:
    obd=None

from .catalog import PARAMETERS

class OBDScanner:
    def __init__(self, port: str|None=None, fast=False, timeout=5):
        if obd is None: raise RuntimeError("Instale a biblioteca OBD: pip install obd")
        self.port=port; self.fast=fast; self.timeout=timeout; self.connection=None

    def connect(self):
        kwargs={"fast":self.fast,"timeout":self.timeout}
        self.connection=obd.OBD(self.port,**kwargs) if self.port else obd.OBD(**kwargs)
        return self.connection.is_connected()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection=None

    @property
    def port_name(self):
        try:return self.connection.port_name()
        except Exception:
            try:return self.connection.get_port_name()
            except Exception:return self.port or ""

    @property
    def protocol(self):
        try:return str(self.connection.protocol_name())
        except Exception:return ""

    def supported(self):
        try:return set(self.connection.supported_commands)
        except Exception:return set()

    def _command(self, names):
        for name in names:
            cmd=getattr(obd.commands,name,None)
            if cmd is not None:return cmd
        return None

    def query(self, names):
        cmd=self._command(names)
        if cmd is None:return None
        try:
            response=self.connection.query(cmd)
            if response is None or response.is_null():return None
            return response.value
        except Exception:return None

    def identity(self):
        vin=self.query(("VIN",))
        return {"vin": str(vin) if vin is not None else None, "port":self.port_name, "protocol":self.protocol}

    def dtcs(self):
        cmd=getattr(obd.commands,"GET_DTC",None)
        if cmd is None:return []
        try:
            r=self.connection.query(cmd)
            return list(r.value or []) if r and not r.is_null() else []
        except Exception:return []

    def clear_dtcs(self):
        cmd=getattr(obd.commands,"CLEAR_DTC",None)
        if cmd is None:return False
        try:
            r=self.connection.query(cmd)
            return r is not None and not r.is_null()
        except Exception:return False

    def freeze_frame(self):
        cmd=getattr(obd.commands,"FREEZE_DTC",None)
        if cmd is None:return None
        try:
            r=self.connection.query(cmd); return r.value if r and not r.is_null() else None
        except Exception:return None

    def status(self):
        cmd=getattr(obd.commands,"STATUS",None)
        if cmd is None:return None
        try:
            r=self.connection.query(cmd); return r.value if r and not r.is_null() else None
        except Exception:return None

    def read_all_supported(self):
        out=[]; supported=self.supported()
        for p in PARAMETERS:
            if not p.command_names:continue
            cmd=self._command(p.command_names)
            if cmd is None or (supported and cmd not in supported):continue
            t=time.perf_counter(); value=self.query(p.command_names); elapsed=(time.perf_counter()-t)*1000
            if value is not None: out.append({"key":p.key,"label":p.label,"unit":p.unit,"value":value,"source":p.source,"response_ms":round(elapsed,1)})
        return out
