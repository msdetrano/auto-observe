# AutoObserve 🚗🔍

**Scanner automotivo em Python + Web**, criado para coletar o máximo possível de dados reais do veículo, armazenar histórico, gerar análise visual e disponibilizar tudo por API e terminal.

> **Em resumo:** o AutoObserve lê o que o carro realmente fornece. Quando um dado não existe ou não é suportado, ele aparece como **N/D / NÃO SUPORTADO**. Não transformamos estimativas em medições reais.

## O que esta versão busca entregar

- 🌐 Dashboard Web servido pelo Python/FastAPI
- 🔌 conexão/desconexão OBD
- 🚗 identificação do veículo por VIN/ECU quando disponível
- 📏 odômetro com origem e nível de confiança
- 📊 mais de 100 parâmetros no catálogo
- 🟢 avaliação: excelente, bom, atenção, ruim ou crítico
- 📈 gráficos e telemetria em tempo real
- 🧠 Health Score por sistema
- 🔧 DTC confirmado, pendente e permanente quando suportado
- 🗑 limpeza de DTC com confirmação
- ❄ Freeze Frame quando suportado
- ✅ Readiness
- 🧩 descoberta de módulos
- 💾 histórico por veículo e sessão
- 🌐 API REST + WebSocket
- 🖥️ relatório técnico no terminal
- 🧮 separação entre REAL, CALCULADO, ESTIMADO e NÃO SUPORTADO

## Arquitetura

```text
Browser
   │ HTML/CSS/JS
   ▼
FastAPI / WebSocket
   │
   ▼
Scanner Engine Python
   ├── python-OBD / ELM327
   ├── PySerial
   ├── CAN / UDS (camada extensível)
   └── Ford OEM (camada extensível)
   │
   ▼
Normalizer + Analytics
   │
   ▼
SQLite (pronto para PostgreSQL)
```

Não usamos Tkinter, PyQt, PySide ou Flet.

## Catálogo 100+

O catálogo inclui parâmetros de:

- identificação e conexão;
- motor;
- admissão;
- combustível e mistura;
- O2/lambda;
- emissões;
- temperaturas;
- elétrica;
- transmissão;
- diagnóstico;
- readiness;
- viagem/consumo;
- métricas calculadas.

O catálogo pode conter parâmetros que determinado veículo não suporta. Isso é proposital: o scanner tenta descobrir e registrar a disponibilidade real.

## Status dos dados

| Tipo | Significado |
|---|---|
| `REAL_ECU` | leitura direta da ECU |
| `REAL_MODULE` | leitura direta de módulo |
| `CALCULATED` | cálculo realizado pelo AutoObserve |
| `ESTIMATED` | estimativa |
| `UNSUPPORTED` | veículo/adaptador não respondeu ou não suporta |

## Avaliação

Cada parâmetro pode receber uma avaliação contextual:

`🟢 EXCELENTE` · `🔵 BOM` · `🟡 ATENÇÃO` · `🟠 RUIM` · `🔴 CRÍTICO` · `⚪ N/D`

As faixas são referências de diagnóstico e não substituem especificações oficiais do fabricante. O sistema não deve declarar defeito com base em uma única leitura.

## Rodando

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py web
```

Abra `http://127.0.0.1:8000`.

Para seu adaptador no macOS, o scanner tenta localizar automaticamente portas `cu.*` e `tty.*`, incluindo adaptadores USB-serial.

```bash
python main.py scan --port /dev/cu.usbserial-A77XUN0V
python main.py live --port /dev/cu.usbserial-A77XUN0V
```

## API

```text
GET  /api/health
GET  /api/vehicles
GET  /api/vehicles/{id}
GET  /api/vehicles/{id}/telemetry
GET  /api/vehicles/{id}/dtcs
GET  /api/vehicles/{id}/health
GET  /api/vehicles/{id}/report
POST /api/obd/connect
POST /api/obd/disconnect
POST /api/diagnostics/read-dtc
POST /api/diagnostics/clear-dtc
WS   /ws/telemetry/{vehicle_id}
```

Swagger/OpenAPI: `/docs`.

## Odômetro

O AutoObserve diferencia explicitamente:

- hodômetro realmente lido de módulo/ECU;
- distância desde DTC;
- distância calculada pela telemetria;
- estimativa.

Nunca apresentar uma distância calculada como se fosse o hodômetro oficial.

## Ford / FORScan

O OBD-II genérico não expõe tudo que uma ferramenta OEM pode acessar. A arquitetura reserva uma camada para CAN/UDS e serviços específicos Ford. O acesso a módulos, configurações e PIDs depende do veículo, ECU, protocolo e adaptador.

## Segurança

A limpeza de DTC altera o estado do veículo e deve exigir confirmação explícita. O sistema registra a sessão e a operação.
