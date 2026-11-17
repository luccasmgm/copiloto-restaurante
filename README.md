# Copiloto de Operação para Restaurantes

Ferramenta de análise para donos de restaurante que combina **dashboard**, **relatório diário automatizado** e um **agente de IA** capaz de responder perguntas em linguagem natural sobre os pedidos do negócio. O projeto foi construído de ponta a ponta como demonstração de como a IA pode ser usada como alavanca para transformar dados em decisões.

## O problema

Donos de restaurante que vendem por iFood, WhatsApp e balcão costumam montar planilhas manualmente e perceber problemas (cancelamentos em alta, entregas lentas, itens com margem baixa) tarde demais.

## A solução

| Necessidade | Como o projeto resolve |
|---|---|
| Visão rápida do negócio | Dashboard com faturamento, pedidos, ticket médio, cancelamento, tempo de entrega e nota |
| Reagir cedo a problemas | Alertas automáticos comparando a última semana com a anterior |
| Economizar tempo de relatório | Endpoint `/relatorio` gera o resumo diário pronto para WhatsApp |
| Fazer perguntas aos dados | Agente de IA com *tool calling*: o modelo escolhe a ferramenta e o código Python calcula os números |
| Usar dados reais | Upload de CSV (`/upload`) com validação e mensagens de erro claras |

**Estimativa de impacto:** cerca de 2,4 horas por semana economizadas, considerando 15 minutos diários de montagem manual de relatório e 30 minutos semanais de análise. É uma estimativa baseada nessas premissas, não uma medição.

## Prévia da interface

A pasta [`docs/`](docs/index.html) contém uma página independente (HTML, CSS e JavaScript puros, sem dependências) com o dashboard, os alertas, o gerador de relatório e um assistente de perguntas. Ela usa dados simulados no próprio navegador e não se conecta à API. Para visualizá-la, abra o arquivo `docs/index.html` no navegador ou publique a pasta com o GitHub Pages.

## Arquitetura

```
 CSV / dados de exemplo
          │
          ▼
   data.py (validação)  ──►  tools.py (funções de análise, Python puro)
                                   ▲                ▲
                                   │                │
                       agent.py (LLM escolhe    relatorio.py
                       qual função chamar)      (texto diário)
                                   │                │
                                   └──── main.py (FastAPI) ────► /chat, /relatorio, /kpis ...
```

**Decisão central:** o modelo de linguagem não calcula nenhum número. Ele apenas decide qual ferramenta chamar, e os valores vêm de funções Python determinísticas e testadas. Isso evita que o agente "invente" dados.

## Tecnologias

- Python 3.11 ou 3.12, FastAPI, Uvicorn, Pydantic
- SDK `openai` (API compatível com OpenAI), funcionando com **Groq** (plano gratuito), **Ollama** (local) ou OpenRouter
- pytest para testes automatizados

## Como executar

Pré-requisito: Python 3.11 ou 3.12.

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Linux / macOS:         source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Acesse a documentação interativa em **http://127.0.0.1:8000/docs**.

### Configuração do agente

Edite o arquivo `.env`:

| Modo | Configuração | Custo |
|---|---|---|
| **LLM via Groq** | Chave gratuita em console.groq.com em `LLM_API_KEY` | Gratuito (com limites de uso) |
| **LLM local (Ollama)** | `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_API_KEY=ollama` | Gratuito |
| **Offline** | Deixe `LLM_API_KEY` vazio | Gratuito, sem internet |

No modo offline, o agente escolhe a ferramenta por palavras-chave, o que permite executar e demonstrar o projeto sem nenhuma conta externa. A resposta do `/chat` informa o modo usado (`llm` ou `offline`) e quais ferramentas foram chamadas.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/kpis?dias=7&deslocamento=0` | Indicadores de um período |
| GET | `/relatorio` | Resumo do último dia, com alertas, pronto para WhatsApp |
| POST | `/chat` | Pergunta em linguagem natural ao agente (`{"texto": "..."}`) |
| POST | `/upload` | Envia um CSV de pedidos |
| GET | `/exemplo.csv` | Baixa o CSV de modelo |
| GET | `/fonte` | Informa a origem dos dados em uso |
| POST | `/reset` | Volta aos dados de exemplo |

### Formato do CSV

Colunas obrigatórias (a ordem não importa): `data, hora, item, quantidade, preco_unitario, custo_unitario, canal, tempo_entrega_min, cancelado`.

Aceita separador vírgula ou ponto e vírgula, decimais com vírgula (`22,50`), datas `AAAA-MM-DD` ou `DD/MM/AAAA`, e `cancelado` como `sim`/`nao`. Veja [`exemplo/pedidos_exemplo.csv`](exemplo/pedidos_exemplo.csv). Os dados de exemplo são sintéticos e incluem um problema simulado nos últimos 7 dias (cancelamentos e entregas piores no iFood à noite) para demonstrar os alertas.

## Testes

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Os testes cobrem as funções de análise, a validação do CSV, o modo offline do agente e os endpoints de upload e relatório.

## Decisões e limitações

- Os dados ficam em memória e valem para todos os usuários do servidor. Isso é adequado para uma demonstração, mas um produto real exigiria banco de dados e isolamento por usuário.
- O relatório é gerado sob demanda; o agendamento e o envio automático (WhatsApp ou e-mail) são o próximo passo natural.
- Em um ambiente de produção, seria necessário restringir o CORS, que hoje aceita qualquer origem.

## Próximos passos

- Integrar a interface visual à API
- Agendar e enviar o relatório automaticamente
- Persistir dados em banco de dados e autenticar usuários

## Estrutura do repositório

```
copiloto-restaurante/
├── backend/
│   ├── app/            # agent.py, data.py, main.py, relatorio.py, tools.py
│   ├── tests/          # testes automatizados
│   ├── requirements.txt
│   └── .env.example
├── docs/        # prévia da interface (https://luccasmgm.github.io/copiloto-restaurante/)
├── exemplo/            # CSV de exemplo
└── README.md
```
