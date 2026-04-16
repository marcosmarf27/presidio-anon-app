# Presidio Anon App — Design Spec

## Contexto

O usuario tem um servico que extrai conteudo de processos judiciais em Markdown/texto. Precisa oferecer uma ferramenta desktop (Windows) que anonimiza dados pessoais (PII) nesses arquivos usando Microsoft Presidio, rodando 100% local — sem enviar dados para nenhum servidor externo.

Foco: processos judiciais brasileiros (pt-BR) com CPF, CNPJ, RG, nomes, enderecos, telefones, e-mails, OAB, datas de nascimento, numero de processo CNJ, NIT/PIS/PASEP e contas bancarias.

---

## Arquitetura Geral

```
Electron (Main Process)
  |-- Spawna Python embutido na inicializacao
  |-- Monitora saude do servidor Python via /health
  |-- Le/salva arquivos via Node.js fs
  |-- IPC com Renderer
  |
  v
Renderer (React + Vite + Tailwind)
  |-- UI: selecao de arquivos, config entidades, previa
  |-- Comunica com backend via fetch http://localhost:PORT
  |
  v
Backend Python (FastAPI + Uvicorn)
  |-- Modelo spaCy pt_core_news_lg carregado uma vez em memoria
  |-- Presidio AnalyzerEngine + AnonymizerEngine
  |-- Recognizers customizados para entidades brasileiras
  |-- Endpoints: POST /anonymize, GET /health
```

### Decisoes de arquitetura

- **Python embutido**: Python Embeddable para Windows empacotado junto com o app. Zero instalacao pelo usuario.
- **Servidor HTTP local**: FastAPI roda como processo filho do Electron. Modelo spaCy carrega uma vez na inicializacao (~10-15s) e fica em memoria. Cada requisicao de anonimizacao leva ~1-2s.
- **Comunicacao**: Electron Main le arquivos do disco (fs) e envia texto via IPC para o Renderer, que faz fetch ao backend Python.
- **Plataforma**: Somente Windows.

---

## Backend Python

### Estrutura de arquivos

```
python-backend/
  server.py          # FastAPI app, endpoints /health e /anonymize
  engine.py          # Inicializacao do AnalyzerEngine com recognizers BR
  recognizers.py     # PatternRecognizers customizados para entidades BR
  mask_config.py     # Regras fixas de mask por entidade
  requirements.txt   # dependencias
```

### Endpoint POST /anonymize

**Request:**
```json
{
  "text": "O reu Joao da Silva, CPF 123.456.789-09...",
  "entities": ["PERSON", "CPF_BR", "PHONE_NUMBER_BR"],
  "language": "pt"
}
```

**Response:**
```json
{
  "anonymized_text": "O reu J**** d* S****, CPF 123.***.***-09...",
  "entities_found": [
    {"type": "PERSON", "text": "Joao da Silva", "start": 6, "end": 19, "score": 0.85},
    {"type": "CPF_BR", "text": "123.456.789-09", "start": 25, "end": 39, "score": 0.9}
  ]
}
```

### Endpoint GET /health

Retorna `{"status": "ready"}` quando o modelo esta carregado. Electron faz polling deste endpoint na inicializacao.

### Entidades suportadas (12 total)

| Entidade | Deteccao | Regex/NER |
|---|---|---|
| PERSON | spaCy NER (PER) | NER |
| LOCATION | spaCy NER (LOC) | NER |
| CPF_BR | `\d{3}\.\d{3}\.\d{3}-\d{2}` | Regex |
| CNPJ_BR | `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` | Regex |
| RG_BR | `\d{1,2}\.\d{3}\.\d{3}-[\dxX]` | Regex |
| PHONE_NUMBER_BR | `\(?\d{2}\)?\s?\d{4,5}-?\d{4}` | Regex |
| EMAIL_ADDRESS | Presidio built-in | Regex |
| OAB_BR | `OAB[/\s]?\w{2}[/\s]?\d{4,6}` | Regex |
| DATE_OF_BIRTH | Datas no formato dd/mm/aaaa com contexto | Regex + contexto |
| NIT_PIS_PASEP | `\d{3}\.\d{5}\.\d{2}-\d{1}` | Regex |
| NUMERO_PROCESSO_CNJ | `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}` | Regex |
| CONTA_BANCARIA | Padroes Ag + CC/CP com digitos | Regex + contexto |

### Regras de mask por entidade

| Entidade | Regra | Exemplo entrada | Exemplo saida |
|---|---|---|---|
| PERSON | 1a letra de cada nome | Joao da Silva | J**** d* S**** |
| CPF_BR | 3 primeiros + 2 ultimos | 123.456.789-09 | 123.***.***-09 |
| CNPJ_BR | 2 primeiros + 2 ultimos | 12.345.678/0001-90 | 12.***.***/****-90 |
| RG_BR | Tudo mascarado exceto ultimo | 12.345.678-9 | **.***.***-9 |
| EMAIL_ADDRESS | 2 primeiras letras + dominio | joao@gmail.com | jo****@gmail.com |
| PHONE_NUMBER_BR | DDD + 2 ultimos | (85) 99999-1234 | (85) *****-**34 |
| LOCATION | 2 primeiras letras | Fortaleza | Fo******** |
| OAB_BR | Estado visivel, numero mascarado | OAB/CE 12345 | OAB/CE ***** |
| DATE_OF_BIRTH | Mostra so o ano | 15/03/1985 | **/**/1985 |
| NIT_PIS_PASEP | 3 primeiros + ultimo | 123.45678.90-1 | 123.*****.**-* |
| NUMERO_PROCESSO_CNJ | Ano + ramo visiveis | 0001234-56.2023.8.06.0001 | *******-**.2023.8.06.**** |
| CONTA_BANCARIA | Tudo mascarado | Ag 1234 CC 56789-0 | Ag **** CC *****-* |

---

## Frontend (Electron + React)

### Stack

- Electron (main + preload + renderer)
- React + TypeScript
- Vite (bundler para o renderer)
- Tailwind CSS
- electron-builder (empacotamento Windows — .exe / NSIS installer)

### Fluxo de telas

**Tela 1 — Selecao de arquivos + configuracao**
- Area de drag-and-drop ou botao "Selecionar arquivos"
- Aceita: .txt, .md
- Limite: 10 arquivos
- Lista dos arquivos selecionados (nome, tamanho, botao remover)
- Painel de checkboxes com as 12 entidades (todas marcadas por padrao)
- Botao "Anonimizar"

**Tela 2 — Processamento**
- Progress bar por arquivo
- Status textual: "Carregando modelo..." -> "Processando arquivo 1 de N..." -> "Concluido"
- Nao bloqueante — pode cancelar

**Tela 3 — Previa do resultado**
- Visualizador de texto com partes mascaradas destacadas (highlight colorido por tipo de entidade)
- Se multiplos arquivos: abas ou lista lateral para navegar
- Resumo: quantidade de entidades encontradas por tipo (badge/chip)
- Botoes: "Salvar todos" e "Voltar"
- Salvar cria arquivo na mesma pasta do original com sufixo `_anonimizado`

### Tela de loading inicial

Enquanto o modelo spaCy carrega (~10-15s no primeiro uso):
- Splash screen ou tela com spinner + mensagem "Carregando motor de anonimizacao..."
- O app fica funcional quando /health retorna 200

---

## Empacotamento

### Python embutido

1. Python Embeddable para Windows (python-3.12.x-embed-amd64.zip, ~15MB)
2. venv pre-buildado com: presidio-analyzer, presidio-anonymizer, fastapi, uvicorn, spacy
3. Modelo pt_core_news_lg (~550MB) pre-baixado
4. Tudo em `resources/python-backend/`

### Electron

- electron-builder com target NSIS (instalador .exe para Windows)
- `extraResources` aponta para `python-backend/`
- Tamanho estimado do instalador: ~700MB-1GB

### Ciclo de vida do processo Python

1. Electron Main inicia -> spawna `python-backend/python.exe server.py`
2. Passa porta disponivel como argumento ou env var
3. Faz polling em `http://localhost:PORT/health` ate receber 200
4. Quando o app fecha -> envia SIGTERM ao processo Python -> mata se nao responder em 5s

---

## Formatos de entrada/saida

| Entrada | Saida | Regra de nome |
|---|---|---|
| `processo.txt` | `processo_anonimizado.txt` | Sufixo `_anonimizado` antes da extensao |
| `decisao.md` | `decisao_anonimizado.md` | Idem |

Para Markdown: processa linha por linha, pula blocos de codigo (entre ```).

---

## Processamento por paragrafo

O texto e processado paragrafo por paragrafo (split por `\n`) para:
- Evitar o limite de 1M chars do spaCy
- Permitir progress granular
- Gerar estatisticas por trecho

---

## Estrutura de pastas do projeto

```
presidio-anon-app/
  electron/
    main.ts              # Electron main process
    preload.ts           # Bridge IPC
  src/
    App.tsx              # Root component
    components/
      FileSelector.tsx   # Drag-and-drop + lista de arquivos
      EntityConfig.tsx   # Checkboxes de entidades
      ProcessingView.tsx # Progress bars
      PreviewView.tsx    # Visualizador com highlights
    hooks/
      usePythonBackend.ts  # Health check, chamadas ao /anonymize
    types/
      index.ts           # Tipos compartilhados
  python-backend/
    server.py
    engine.py
    recognizers.py
    mask_config.py
    requirements.txt
  package.json
  vite.config.ts
  electron-builder.yml
  tailwind.config.js
  tsconfig.json
```

---

## Verificacao

Para testar end-to-end:

1. Instalar dependencias Python: `pip install -r python-backend/requirements.txt`
2. Baixar modelo: `python -m spacy download pt_core_news_lg`
3. Iniciar backend: `python python-backend/server.py`
4. Testar endpoint: `curl -X POST http://localhost:8000/anonymize -H "Content-Type: application/json" -d '{"text": "Joao da Silva, CPF 123.456.789-09", "entities": ["PERSON", "CPF_BR"], "language": "pt"}'`
5. Iniciar frontend: `npm run dev` (Vite + Electron)
6. Testar fluxo completo: selecionar arquivo .txt -> anonimizar -> verificar previa -> salvar
7. Build: `npm run build` -> verificar instalador .exe funciona em Windows limpo
