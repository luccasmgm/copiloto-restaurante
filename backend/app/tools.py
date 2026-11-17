"""Ferramentas de análise (Python puro). Funcionam com qualquer CSV carregado.

Períodos: "dias" = quantos dias contar, terminando no último dia dos dados;
"deslocamento" = quantos dias voltar no tempo. Exemplo: kpis(7, 7) é a semana anterior.
"""
from collections import Counter

from . import data


def _periodo(dias: int, deslocamento: int) -> list[dict]:
    fim = max(p["dia"] for p in data.PEDIDOS) - deslocamento
    return [p for p in data.PEDIDOS if fim - dias + 1 <= p["dia"] <= fim]


def _faturamento(ps: list[dict]) -> float:
    return sum(p["preco"] * p["qtd"] for p in ps if not p["cancelado"])


def kpis(dias: int = 7, deslocamento: int = 0) -> dict:
    ps = _periodo(dias, deslocamento)
    ok = [p for p in ps if not p["cancelado"]]
    entregas = [p["entrega_min"] for p in ok if p["entrega_min"] > 0]
    return {
        "pedidos": len(ps),
        "faturamento_reais": round(_faturamento(ps)),
        "ticket_medio_reais": round(_faturamento(ps) / len(ok), 2) if ok else 0,
        "taxa_cancelamento_pct": round(100 * (1 - len(ok) / len(ps)), 1) if ps else 0,
        "entrega_media_min": round(sum(entregas) / len(entregas), 1) if entregas else 0,
    }


def top_itens(n: int = 3) -> list[dict]:
    fat = Counter()  # dicionário que soma valores por chave
    for p in data.PEDIDOS:
        if not p["cancelado"]:
            fat[p["item"]] += p["preco"] * p["qtd"]
    return [{"item": nome, "faturamento_reais": round(v)} for nome, v in fat.most_common(n)]


def cancelamento_por_canal(dias: int = 7, deslocamento: int = 0) -> list[dict]:
    ps = _periodo(dias, deslocamento)
    saida = []
    for canal in sorted({p["canal"] for p in ps}):
        do_canal = [p for p in ps if p["canal"] == canal]
        saida.append({"canal": canal,
                      "cancelamento_pct": round(100 * sum(p["cancelado"] for p in do_canal) / len(do_canal), 1)})
    return saida


def horarios_pico(n: int = 3) -> list[dict]:
    c = Counter(p["hora"] for p in data.PEDIDOS)
    return [{"hora": h, "pedidos": q} for h, q in c.most_common(n)]


def margem_itens() -> list[dict]:
    precos = {p["item"]: (p["preco"], p["custo"]) for p in data.PEDIDOS}  # último valor de cada item
    m = [{"item": i, "margem_pct": round(100 * (pr - c) / pr, 1)} for i, (pr, c) in precos.items() if pr > 0]
    return sorted(m, key=lambda x: x["margem_pct"])
