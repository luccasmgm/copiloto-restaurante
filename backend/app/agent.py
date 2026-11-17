"""Agente com tool calling (uso de ferramentas) em API compatível com OpenAI.

Funciona com Groq, Ollama, OpenRouter e outros: só mudam 3 variáveis no .env.
Sem chave, cai no "modo offline", que escolhe a ferramenta por palavras-chave.

Fluxo com LLM:
 1. Enviamos a pergunta + a lista de ferramentas.
 2. O modelo pede "chame a ferramenta X com estes argumentos".
 3. NÓS executamos a função Python e devolvemos o resultado.
 4. Repetimos até o modelo escrever a resposta final.
"""
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from . import tools

load_dotenv()
CHAVE = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
MODELO = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

SYSTEM = ("Você é um analista de operações de restaurante. Responda em português, de forma "
          "objetiva. Use SEMPRE as ferramentas para obter números; nunca invente valores. "
          "Períodos: 'dias' é quantos dias contar até o fim dos dados e 'deslocamento' é quantos dias voltar. "
          "Última semana = dias=7, deslocamento=0; semana anterior = dias=7, deslocamento=7.")

_PERIODO = {"dias": {"type": "integer", "description": "Quantos dias contar (padrão 7)"},
            "deslocamento": {"type": "integer", "description": "Quantos dias voltar no tempo (padrão 0)"}}


def _ferramenta(nome, descricao, props=None):
    return {"type": "function", "function": {
        "name": nome, "description": descricao,
        "parameters": {"type": "object", "properties": props or {}}}}


FERRAMENTAS = [
    _ferramenta("kpis", "Faturamento, pedidos, ticket médio, cancelamento e tempo de entrega de um período.", _PERIODO),
    _ferramenta("top_itens", "Itens com maior faturamento.", {"n": {"type": "integer"}}),
    _ferramenta("cancelamento_por_canal", "Taxa de cancelamento por canal (iFood, WhatsApp).", _PERIODO),
    _ferramenta("horarios_pico", "Horários com mais pedidos.", {"n": {"type": "integer"}}),
    _ferramenta("margem_itens", "Margem de lucro de cada item, da menor para a maior."),
]
FUNCOES = {f["function"]["name"]: getattr(tools, f["function"]["name"]) for f in FERRAMENTAS}


def _perguntar_llm(texto: str) -> dict:
    client = OpenAI(api_key=CHAVE, base_url=BASE_URL)
    mensagens = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": texto}]
    usadas = []
    for _ in range(5):  # limite de voltas, evita loop infinito
        resp = client.chat.completions.create(model=MODELO, messages=mensagens,
                                              tools=FERRAMENTAS, max_tokens=1000)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"resposta": msg.content or "", "ferramentas_usadas": usadas, "modo": "llm"}
        mensagens.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in msg.tool_calls]})
        for c in msg.tool_calls:
            args = json.loads(c.function.arguments or "{}")
            try:
                saida = FUNCOES[c.function.name](**args)  # ** desempacota o dict em argumentos
            except Exception as e:  # devolve o erro ao modelo, que pode se corrigir
                saida = {"erro": str(e)}
            usadas.append({"nome": c.function.name, "argumentos": args})
            mensagens.append({"role": "tool", "tool_call_id": c.id,
                              "content": json.dumps(saida, ensure_ascii=False)})
    return {"resposta": "Não consegui concluir a análise.", "ferramentas_usadas": usadas, "modo": "llm"}


# Modo offline: (padrão regex, ferramenta, argumentos). A primeira que casar vence.
_REGRAS = [
    (r"mais vend|top|ranking|melhor item", "top_itens", {"n": 3}),
    (r"cancel", "cancelamento_por_canal", {}),
    (r"hor[aá]rio|pico|movimento", "horarios_pico", {}),
    (r"margem|lucro", "margem_itens", {}),
]


def _perguntar_offline(texto: str) -> dict:
    t = texto.lower()
    nome, args = next(((n, a) for p, n, a in _REGRAS if re.search(p, t)), ("kpis", {}))
    saida = FUNCOES[nome](**args)
    return {"resposta": f"(modo offline) Resultado de {nome}: {json.dumps(saida, ensure_ascii=False)}",
            "ferramentas_usadas": [{"nome": nome, "argumentos": args}], "modo": "offline"}


def perguntar(texto: str) -> dict:
    return _perguntar_llm(texto) if CHAVE else _perguntar_offline(texto)
