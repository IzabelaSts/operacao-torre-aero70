#!/usr/bin/env python3
# torre.py - CLI Operação Torre 1978 (final)

import argparse
import csv
from datetime import datetime, time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DADOS_DIR = BASE_DIR / "dados"
LOGS_DIR = BASE_DIR / "logs"
REL_DIR = BASE_DIR / "relatorios"

PLANOS_VOO = DADOS_DIR / "planos_voo.csv"
PISTAS_TXT = DADOS_DIR / "pistas.txt"
FROTA_CSV = DADOS_DIR / "frota.csv"
PILOTOS_CSV = DADOS_DIR / "pilotos.csv"
METAR_TXT = DADOS_DIR / "metar.txt"
NOTAM_TXT = DADOS_DIR / "notam.txt"
FILA_DECOLAGEM = DADOS_DIR / "fila_decolagem.txt"
FILA_POUSO = DADOS_DIR / "fila_pouso.txt"
LOG_FILE = LOGS_DIR / "torre.log"


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {msg}\n")


def read_csv(file_path):
    with open(file_path, newline='') as f:
        return list(csv.DictReader(f))


def read_txt_lines(file_path):
    if not file_path.exists():
        return []
    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]


def parse_pistas():
    pistas = {}
    for line in read_txt_lines(PISTAS_TXT):
        pista, status = line.split(",")
        pistas[pista] = status
    return pistas


def parse_metar():
    metars = {}
    for line in read_txt_lines(METAR_TXT):
        parts = line.split()
        hora = parts[0]
        vis_idx = parts.index("VIS")
        vis = int(parts[vis_idx + 1].replace("KM", ""))
        metars[hora] = {"VIS": vis, "raw": line}
    return metars


def parse_notam():
    notams = []
    for line in read_txt_lines(NOTAM_TXT):
        if line.startswith("PISTA"):
            tokens = line.split()
            pista = tokens[1]
            status = tokens[2]
            window = tokens[3]
            start, end = window.split("-")
            text = " ".join(tokens[4:]) if len(tokens) > 4 else ""
            notams.append({"pista": pista, "status": status, "start": start, "end": end, "text": text})
        else:
            notams.append({"text": line})
    return notams


def hora_str_to_time(hora_str):
    return datetime.strptime(hora_str, "%H:%M").time()


def importar_dados():
    required_files = [PLANOS_VOO, PISTAS_TXT, FROTA_CSV, PILOTOS_CSV, METAR_TXT, NOTAM_TXT]
    missing = [str(f) for f in required_files if not f.exists()]
    if missing:
        msg = f"Erro: arquivos ausentes: {', '.join(missing)}"
        print(msg)
        log(msg)
        return
    FILA_DECOLAGEM.write_text("")
    FILA_POUSO.write_text("")
    print("Dados importados com sucesso.")
    log("Comando importar-dados executado com sucesso.")


def listar(sort_by="voo"):
    voos = read_csv(PLANOS_VOO)
    if sort_by == "prioridade":
        voos.sort(key=lambda v: (-int(v["prioridade"]), v["etd"]))
    elif sort_by == "etd":
        voos.sort(key=lambda v: v["etd"])
    elif sort_by in ["tipo", "voo"]:
        voos.sort(key=lambda v: v[sort_by])
    print(f"{'Voo':<8} {'Origem':<6} {'Destino':<6} {'ETD':<6} {'ETA':<6} {'Aeronave':<8} {'Tipo':<10} {'Prio':<4} {'Pista':<6}")
    for v in voos:
        print(f"{v['voo']:<8} {v['origem']:<6} {v['destino']:<6} {v['etd']:<6} {v['eta']:<6} {v['aeronave']:<8} {v['tipo']:<10} {v['prioridade']:<4} {v['pista_pref']:<6}")


def enfileirar(tipo, voo_codigo):
    voos = read_csv(PLANOS_VOO)
    voo = next((v for v in voos if v["voo"] == voo_codigo), None)
    if not voo:
        msg = f"Voo {voo_codigo} não encontrado."
        print(msg)
        log(msg)
        return

    fila_file = FILA_DECOLAGEM if tipo == "decolagem" else FILA_POUSO
    fila_voos = read_txt_lines(fila_file)

    if any(voo_codigo in line for line in fila_voos):
        msg = f"Falha: voo {voo_codigo} já está na fila"
        print(msg)
        log(msg)
        return

    fila_file.write_text("\n".join(fila_voos + [f"{voo_codigo};{voo['etd']};{voo['prioridade']};{voo['pista_pref']}"]) + "\n")
    msg = f"Voo {voo_codigo} enfileirado para {tipo}"
    print(msg)
    log(msg)


def autorizar(tipo, pista):
    fila_file = FILA_DECOLAGEM if tipo == "decolagem" else FILA_POUSO
    fila_voos = read_txt_lines(fila_file)
    if not fila_voos:
        msg = f"Nenhum voo na fila de {tipo}"
        print(msg)
        log(msg)
        return

    pistas = parse_pistas()
    if pistas.get(pista) != "ABERTA":
        msg = f"NEGADO: pista {pista} não está ABERTA"
        print(msg)
        log(msg)
        return

    voo_info = fila_voos[0].split(";")
    voo_codigo = voo_info[0]
    voo_hora = hora_str_to_time(voo_info[1])

    # NOTAM
    for n in parse_notam():
        if n.get("pista") == pista and n["status"] == "FECHADA":
            start = hora_str_to_time(n["start"])
            end = hora_str_to_time(n["end"])
            if start <= voo_hora <= end:
                msg = f"NEGADO: NOTAM ativa na pista {pista} ({n['text']}) no horário {voo_info[1]}"
                print(msg)
                log(msg)
                return

    # METAR / visibilidade
    metars = parse_metar()
    vis = 999
    voo_dt = voo_hora
    metar_times = sorted([hora_str_to_time(h) for h in metars.keys()])
    selected_metar = None
    for mt in metar_times:
        if mt <= voo_dt:
            selected_metar = mt
    if selected_metar:
        vis = metars[selected_metar.strftime("%H:%M")]["VIS"]

    if vis < 6:
        msg = f"NEGADO: visibilidade baixa ({vis}KM), apenas 1 operação por vez"
        print(msg)
        log(msg)
        return

    # Autoriza
    fila_voos.pop(0)
    fila_file.write_text("\n".join(fila_voos) + ("\n" if fila_voos else ""))
    msg = f"AUTORIZADO: voo {voo_codigo} em pista {pista}"
    print(msg)
    log(msg)


def status():
    pistas = parse_pistas()
    print("Pistas:")
    for p, s in pistas.items():
        print(f"  {p}: {s}")
    fila_d = read_txt_lines(FILA_DECOLAGEM)
    fila_p = read_txt_lines(FILA_POUSO)
    print(f"Fila de decolagem ({len(fila_d)}): {fila_d[:3]}")
    print(f"Fila de pouso ({len(fila_p)}): {fila_p[:3]}")
    print("NOTAMs ativos:")
    for n in parse_notam():
        print(f"  {n}")


def relatorio():
    rel_file = REL_DIR / f"operacao_{datetime.now().strftime('%Y%m%d')}.txt"
    REL_DIR.mkdir(parents=True, exist_ok=True)
    with open(rel_file, "w") as f:
        f.write("Relatório de turno\n")
        f.write(f"Total de decolagens na fila: {len(read_txt_lines(FILA_DECOLAGEM))}\n")
        f.write(f"Total de pousos na fila: {len(read_txt_lines(FILA_POUSO))}\n")
    print(f"Relatório gerado: {rel_file}")
    log("Relatório gerado.")


def main():
    parser = argparse.ArgumentParser(description="Operação TORRE 1978 CLI")
    sub = parser.add_subparsers(dest="comando")

    sub.add_parser("importar-dados")

    l_parser = sub.add_parser("listar")
    l_parser.add_argument("--por", choices=["voo", "etd", "tipo", "prioridade"], default="voo")

    e_parser = sub.add_parser("enfileirar")
    e_parser.add_argument("tipo", choices=["decolagem", "pouso"])
    e_parser.add_argument("--voo", required=True)

    a_parser = sub.add_parser("autorizar")
    a_parser.add_argument("tipo", choices=["decolagem", "pouso"])
    a_parser.add_argument("--pista", required=True)

    sub.add_parser("status")
    sub.add_parser("relatorio")

    args = parser.parse_args()
    if args.comando == "importar-dados":
        importar_dados()
    elif args.comando == "listar":
        listar(args.por)
    elif args.comando == "enfileirar":
        enfileirar(args.tipo, args.voo)
    elif args.comando == "autorizar":
        autorizar(args.tipo, args.pista)
    elif args.comando == "status":
        status()
    elif args.comando == "relatorio":
        relatorio()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
