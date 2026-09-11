from __future__ import annotations
import argparse, time
from rich.console import Console
from rich.table import Table
from .obd_engine import OBDScanner
from .catalog import PARAMETERS

console=Console()

def scan(port=None):
    s=OBDScanner(port,timeout=8)
    if not s.connect(): console.print('[red]Não foi possível conectar.[/red]'); return 1
    try:
        ident=s.identity(); console.print(f'\n[bold]AUTO OBSERVE — FULL SCAN[/bold]\nVIN: {ident.get("vin") or "N/D"}\nPorta: {s.port_name}\nProtocolo: {s.protocol}\n')
        codes=s.dtcs(); console.print(f'DTC: {len(codes)}')
        rows=s.read_all_supported(); table=Table(title=f'Dados respondidos ({len(rows)})'); table.add_column('Parâmetro'); table.add_column('Valor'); table.add_column('Unidade'); table.add_column('Fonte')
        for x in rows: table.add_row(x['label'],str(x['value']),x['unit'],x['source'])
        console.print(table); return 0
    finally:s.close()

def live(port=None, interval=2):
    s=OBDScanner(port,timeout=8)
    if not s.connect(): console.print('[red]Não foi possível conectar.[/red]'); return 1
    try:
        console.print('[bold green]🟢 AUTO OBSERVE LIVE[/bold green] — Ctrl+C para sair')
        while True:
            rows=s.read_all_supported(); table=Table(); table.add_column('Parâmetro'); table.add_column('Valor'); table.add_column('Unidade')
            for x in rows: table.add_row(x['label'],str(x['value']),x['unit'])
            console.clear(); console.print(table); time.sleep(interval)
    except KeyboardInterrupt:return 0
    finally:s.close()

def main():
    p=argparse.ArgumentParser(prog='autoobserve'); sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('scan','live'):
        sp=sub.add_parser(name); sp.add_argument('--port',default=None); sp.set_defaults(fn=scan if name=='scan' else live)
    a=p.parse_args(); raise SystemExit(a.fn(a.port))
