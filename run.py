import argparse
import uvicorn
from autoobserve.app import app
from autoobserve.cli import scan, live

p=argparse.ArgumentParser(description='AutoObserve — scanner OBD-II em Python')
sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('web',help='inicia o dashboard web')
s=sub.add_parser('scan',help='faz uma leitura completa'); s.add_argument('--port')
l=sub.add_parser('live',help='telemetria no terminal'); l.add_argument('--port')
a=p.parse_args()
if a.command=='web': uvicorn.run(app,host='127.0.0.1',port=8000)
elif a.command=='scan': raise SystemExit(scan(a.port))
elif a.command=='live': raise SystemExit(live(a.port))
