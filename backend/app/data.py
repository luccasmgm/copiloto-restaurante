"""Dados do restaurante: gera um exemplo e lê CSVs enviados pelo usuário.

Os dois caminhos passam pela mesma função (_converter), então o exemplo
e os arquivos reais são tratados exatamente do mesmo jeito.
"""
import csv
import io
import random
from datetime import date, datetime, timedelta

# Colunas obrigatórias do CSV (a ordem não importa)
COLUNAS = ["data", "hora", "item", "quantidade", "preco_unitario",
           "custo_unitario", "canal", "tempo_entrega_min", "cancelado"]
MENU = [("X-Burger", 28, 11), ("X-Bacon", 34, 14), ("Batata Frita", 16, 5),
        ("Combo Família", 79, 32), ("Açaí 500ml", 19, 7), ("Refrigerante", 8, 3),
        ("Pizza Média", 48, 18), ("Salada Caesar", 26, 10)]
CANAIS = ["iFood", "WhatsApp", "Balcão"]

PEDIDOS: list[dict] = []   # dados em uso (a lista é alterada "no lugar")
FONTE: dict = {}           # informações sobre a origem dos dados


def gerar_linhas(seed: int = 42, fim: date = date(2026, 11, 16)) -> list[dict]:
    """Simula 30 dias de pedidos. A semente fixa faz o resultado ser sempre igual."""
    rng = random.Random(seed)
    linhas = []
    for dia in range(30):
        fim_de_semana = (dia + 1) % 7 < 2
        for _ in range(int(26 + rng.random() * 10 + (14 if fim_de_semana else 0))):
            r = rng.random()
            hora = 11 + int(rng.random() * 3) if r < 0.42 else (
                18 + int(rng.random() * 4) if rng.random() < 0.8 else 15 + int(rng.random() * 3))
            r = rng.random()
            canal = 0 if r < 0.55 else 1 if r < 0.8 else 2
            nome, preco, custo = MENU[int((rng.random() ** 1.4) * len(MENU))]
            # Problema simulado nos últimos 7 dias: iFood à noite fica mais lento
            lento = dia >= 23 and hora >= 19 and canal == 0
            entrega = 0 if canal == 2 else round(
                26 + (7 if hora >= 19 or hora <= 13 else 0) + rng.random() * 12 + (11 if lento else 0))
            cancelado = rng.random() < 0.03 + (0.04 if dia >= 23 and canal == 0 else 0)
            qtd = 1 + int(rng.random() * 2.2)
            linhas.append({"data": (fim - timedelta(days=29 - dia)).isoformat(), "hora": hora,
                           "item": nome, "quantidade": qtd, "preco_unitario": preco,
                           "custo_unitario": custo, "canal": CANAIS[canal],
                           "tempo_entrega_min": entrega, "cancelado": "sim" if cancelado else "nao"})
    return linhas


def csv_exemplo() -> str:
    saida = io.StringIO()
    w = csv.DictWriter(saida, fieldnames=COLUNAS)
    w.writeheader()
    w.writerows(gerar_linhas())
    return saida.getvalue()


def _data(txt: str) -> date:
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt, formato).date()
        except ValueError:
            pass
    raise ValueError("data inválida")


def _num(v) -> float:
    # aceita vírgula decimal ("12,50"), comum em planilhas brasileiras; vazio vira 0
    return float(str(v or "0").strip().replace(",", "."))


def _converter(linhas) -> list[dict]:
    """Valida cada linha e converte para o formato interno."""
    pedidos, erros = [], []
    for n, r in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        try:
            hora = int(_num(r["hora"]))
            item = r["item"].strip()
            if not item or not 0 <= hora <= 23:
                raise ValueError
            pedidos.append({
                "data": _data(str(r["data"]).strip()), "hora": hora, "item": item,
                "qtd": int(_num(r["quantidade"])), "preco": _num(r["preco_unitario"]),
                "custo": _num(r["custo_unitario"]), "canal": r["canal"].strip(),
                "entrega_min": _num(r["tempo_entrega_min"]),
                "cancelado": str(r["cancelado"]).strip().lower() in ("1", "sim", "s", "true", "yes")})
        except (ValueError, TypeError, KeyError, AttributeError):
            erros.append(str(n))
            if len(erros) >= 5:
                break
    if erros:
        raise ValueError("Valores inválidos nas linhas: " + ", ".join(erros) + ".")
    if not pedidos:
        raise ValueError("O arquivo não tem pedidos.")
    base = min(p["data"] for p in pedidos)
    for p in pedidos:
        p["dia"] = (p["data"] - base).days  # 0 = primeiro dia dos dados
    return pedidos


def processar_csv(conteudo: bytes) -> list[dict]:
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")  # Excel antigo no Windows
    primeira = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primeira.count(";") > primeira.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=separador)
    leitor.fieldnames = [c.strip().lower() for c in (leitor.fieldnames or [])]
    faltando = [c for c in COLUNAS if c not in leitor.fieldnames]
    if faltando:
        raise ValueError("Colunas ausentes: " + ", ".join(faltando) + ".")
    linhas = list(leitor)
    if len(linhas) > 20000:
        raise ValueError("Arquivo grande demais (máximo de 20.000 pedidos).")
    return _converter(linhas)


def carregar(pedidos: list[dict], origem: str) -> dict:
    PEDIDOS[:] = pedidos
    inicio, fim = min(p["data"] for p in pedidos), max(p["data"] for p in pedidos)
    FONTE.update(origem=origem, pedidos=len(pedidos), inicio=inicio.isoformat(),
                 fim=fim.isoformat(), dias=(fim - inicio).days + 1)
    return FONTE


carregar(_converter(gerar_linhas()), "exemplo")
