"""Relatório diário pronto para enviar (ex.: WhatsApp).

Reaproveita as mesmas ferramentas do agente: nenhum número é calculado aqui.
"""
from datetime import date

from . import data, tools


def _n(v, casas=1) -> str:
    return f"{v:.{casas}f}".replace(".", ",")  # 6.1 -> "6,1"


def _variacao(atual: float, anterior: float) -> str:
    if not anterior:
        return ""
    v = 100 * (atual - anterior) / anterior
    return f" ({'+' if v >= 0 else ''}{_n(v)}% vs. dia anterior)"


def gerar() -> dict:
    hoje, ontem = tools.kpis(1, 0), tools.kpis(1, 1)
    sem, ant = tools.kpis(7, 0), tools.kpis(7, 7)
    alertas = []

    if ant["pedidos"] and sem["taxa_cancelamento_pct"] > max(5, ant["taxa_cancelamento_pct"] * 1.3):
        pior = max(tools.cancelamento_por_canal(), key=lambda c: c["cancelamento_pct"])
        alertas.append(f"Cancelamentos subiram para {_n(sem['taxa_cancelamento_pct'])}% na semana "
                       f"(antes {_n(ant['taxa_cancelamento_pct'])}%). Canal mais afetado: "
                       f"{pior['canal']} ({_n(pior['cancelamento_pct'])}%).")
    if ant["entrega_media_min"] and sem["entrega_media_min"] > ant["entrega_media_min"] + 3:
        alertas.append(f"Entrega média subiu para {round(sem['entrega_media_min'])} min "
                       f"(antes {round(ant['entrega_media_min'])} min). Verifique o turno da noite.")
    margens = tools.margem_itens()
    if margens:
        alertas.append(f"Item com menor margem: {margens[0]['item']} ({_n(margens[0]['margem_pct'])}%).")

    dia = date.fromisoformat(data.FONTE["fim"]).strftime("%d/%m")
    lider = tools.top_itens(1)[0]["item"]
    linhas = [f"📊 Resumo de {dia}",
              f"Faturamento: R$ {hoje['faturamento_reais']}{_variacao(hoje['faturamento_reais'], ontem['faturamento_reais'])}",
              f"Pedidos: {hoje['pedidos']} | Ticket médio: R$ {_n(hoje['ticket_medio_reais'], 2)}",
              f"Cancelamento: {_n(hoje['taxa_cancelamento_pct'])}% | Entrega média: {round(hoje['entrega_media_min'])} min",
              f"Item líder do período: {lider}"]
    if alertas:
        linhas += ["", "⚠️ Atenção:"] + [f"- {a}" for a in alertas]
    return {"texto": "\n".join(linhas), "alertas": alertas}
