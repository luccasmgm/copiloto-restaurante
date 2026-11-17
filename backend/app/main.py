"""API web (FastAPI). Rode com: uvicorn app.main:app --reload"""
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import agent, data, relatorio, tools

app = FastAPI(title="Copiloto de Operação para Restaurantes")
# CORS permite que o front-end (outra origem) chame esta API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Pergunta(BaseModel):  # Pydantic valida o JSON recebido automaticamente
    texto: str


@app.get("/")
def raiz():
    return {"status": "online", "documentacao": "/docs"}


@app.get("/kpis")
def get_kpis(dias: int = 7, deslocamento: int = 0):
    return tools.kpis(dias, deslocamento)


@app.get("/relatorio")
def get_relatorio():
    """Relatório do último dia dos dados, pronto para enviar por WhatsApp."""
    return relatorio.gerar()


@app.get("/fonte")
def get_fonte():
    """Informa de onde vêm os dados em uso (exemplo ou arquivo enviado)."""
    return data.FONTE


@app.get("/exemplo.csv")
def baixar_exemplo():
    """CSV de modelo: mostra o formato esperado no upload."""
    return Response(data.csv_exemplo(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=pedidos_exemplo.csv"})


@app.post("/upload")
async def upload(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()
    if len(conteudo) > 2_000_000:
        raise HTTPException(status_code=413, detail="Arquivo maior que 2 MB.")
    try:
        pedidos = data.processar_csv(conteudo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return data.carregar(pedidos, arquivo.filename or "upload")


@app.post("/reset")
def reset():
    """Volta para os dados de exemplo."""
    return data.carregar(data._converter(data.gerar_linhas()), "exemplo")


@app.post("/chat")
def chat(p: Pergunta):
    try:
        return agent.perguntar(p.texto)
    except Exception as e:  # ex.: chave de API ausente
        raise HTTPException(status_code=500, detail=str(e))
