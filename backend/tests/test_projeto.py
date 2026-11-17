"""Testes automatizados. Rode com: pytest (dentro da pasta backend)."""
import pytest
from fastapi.testclient import TestClient

from app import agent, data, tools
from app.main import app

CABECALHO = "data;hora;item;quantidade;preco_unitario;custo_unitario;canal;tempo_entrega_min;cancelado\n"


@pytest.fixture(autouse=True)
def dados_de_exemplo():
    """Antes de cada teste, volta aos dados de exemplo (os testes não interferem entre si)."""
    data.carregar(data._converter(data.gerar_linhas()), "exemplo")


def test_kpis_com_valores_coerentes():
    k = tools.kpis()
    assert k["pedidos"] > 0
    assert 0 <= k["taxa_cancelamento_pct"] <= 100


def test_semanas_nao_se_sobrepoem():
    assert tools.kpis(7, 0)["pedidos"] + tools.kpis(7, 7)["pedidos"] == tools.kpis(14, 0)["pedidos"]


def test_top_itens_em_ordem_decrescente():
    fat = [i["faturamento_reais"] for i in tools.top_itens(5)]
    assert fat == sorted(fat, reverse=True)


def test_margens_em_ordem_crescente():
    m = [i["margem_pct"] for i in tools.margem_itens()]
    assert m == sorted(m)


def test_csv_com_ponto_e_virgula_e_decimal_brasileiro():
    csv = CABECALHO + "01/11/2026;12;Marmita;2;22,50;9,00;iFood;35;nao\n"
    pedidos = data.processar_csv(csv.encode("latin-1"))
    assert pedidos[0]["preco"] == 22.5 and pedidos[0]["qtd"] == 2


def test_csv_sem_colunas_obrigatorias():
    with pytest.raises(ValueError, match="Colunas ausentes"):
        data.processar_csv(b"a,b\n1,2")


def test_csv_com_hora_invalida():
    csv = CABECALHO + "01/11/2026;25;Marmita;1;22,50;9,00;iFood;35;nao\n"
    with pytest.raises(ValueError, match="linhas: 2"):
        data.processar_csv(csv.encode())


def test_modo_offline_escolhe_a_ferramenta(monkeypatch):
    monkeypatch.setattr(agent, "CHAVE", "")  # sem chave de API
    r = agent.perguntar("qual o item mais vendido?")
    assert r["modo"] == "offline"
    assert r["ferramentas_usadas"][0]["nome"] == "top_itens"


def test_api_upload_e_relatorio():
    c = TestClient(app)
    csv = CABECALHO + "01/11/2026;12;Marmita;2;22,50;9,00;iFood;35;nao\n"
    r = c.post("/upload", files={"arquivo": ("pedidos.csv", csv.encode())})
    assert r.status_code == 200 and r.json()["origem"] == "pedidos.csv"
    assert "Marmita" in c.get("/relatorio").json()["texto"]
    assert c.post("/upload", files={"arquivo": ("x.csv", b"a,b\n1,2")}).status_code == 400
