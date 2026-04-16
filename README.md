# Presidio Anon App

Aplicativo desktop para **anonimização de PII em textos jurídicos brasileiros**.
Roda 100% local — nenhum dado sai do computador do usuário.

## O que faz

- Detecta e mascara dados pessoais em termos de audiência, sentenças, petições e similares.
- Suporta arquivos `.txt`, `.md` e `.rtf`.
- Reconhece entidades típicas do contexto jurídico BR:
  - **Pessoas** (NER via BERT fine-tuned em LeNER-Br).
  - **Documentos brasileiros**: CPF, CNPJ, RG, PIS/NIT, OAB, número de processo CNJ.
  - **Contato**: telefone (incl. `+55`), e-mail, endereço.
  - **Outros**: datas de nascimento, conta bancária.
- Validação de dígito verificador de CPF/CNPJ/PIS/processo CNJ — evita falsos positivos e eleva o score de candidatos confirmados.
- Deny list e palavras de contexto externalizadas em JSON para customização sem editar código.

## Stack

- **Desktop**: Electron + React + TypeScript + Tailwind.
- **Backend NLP**: FastAPI + [Microsoft Presidio](https://microsoft.github.io/presidio/).
- **Modelo NER (default)**: [`pierreguillou/ner-bert-large-cased-pt-lenerbr`](https://huggingface.co/pierreguillou/ner-bert-large-cased-pt-lenerbr) (F1 ≈ 0.91 em LeNER-Br).
- **Fallback leve**: `pt_core_news_lg` do spaCy (modo `PRESIDIO_NLP_MODE=spacy`).

## Rodar em desenvolvimento

Pré-requisitos: Node 20+, Python 3.12.

```bash
# Frontend
npm install

# Backend Python
python3 -m venv .venv
.venv/bin/pip install -r python-backend/requirements.txt
.venv/bin/python -m spacy download pt_core_news_lg
.venv/bin/python -m spacy download pt_core_news_sm

# Dev (Electron + Vite + backend)
npm run dev:electron
```

Na primeira execução em modo `transformer`, o modelo BERT (~1.7 GB) é
baixado do HuggingFace e guardado no cache local (`~/.cache/huggingface`).

Para usar o modo leve sem transformer:
```bash
PRESIDIO_NLP_MODE=spacy npm run dev:electron
```

## Testes

```bash
.venv/bin/pytest python-backend/tests -v
```

Os testes medem recall e precisão sobre uma fixture jurídica sintética
(sem dados reais). Ver `python-backend/tests/fixtures/`.

## Uso via linha de comando (CLI)

Além da GUI, o app instala uma CLI que funciona no **cmd/PowerShell** e no **WSL**.
Basta abrir a tela **Linha de comando** na barra lateral e clicar em **Ativar no Windows**
e/ou **Ativar no WSL**. Depois, em qualquer terminal:

```bash
# Arquivo -> stdout
presidio-anon audiencia.txt

# Arquivo -> arquivo
presidio-anon audiencia.txt -o audiencia_anon.txt

# Pipe (Unix / WSL)
cat audiencia.txt | presidio-anon --entities PERSON,CPF_BR

# Batch in-place
presidio-anon *.txt --in-place

# Formato JSON (ideal para agentes como Claude Code)
presidio-anon audiencia.txt -q --format json
```

Saída JSON inclui `anonymized_text` e a lista `entities_found` com tipo,
texto original, posição (`start`/`end`) e score de cada PII detectada.

Flags:
- `-e, --entities` — lista separada por vírgula (PERSON, CPF_BR, CNPJ_BR, RG_BR, PHONE_NUMBER_BR, EMAIL_ADDRESS, LOCATION, OAB_BR, DATE_OF_BIRTH, NIT_PIS_PASEP, NUMERO_PROCESSO_CNJ, CONTA_BANCARIA). Default: todas.
- `-f, --format text|json` — formato de saída.
- `-o, --output` — arquivo de saída (default stdout).
- `--output-dir` — pasta para batch (com múltiplos arquivos).
- `--in-place` — sobrescreve os inputs.
- `--nlp-mode transformer|spacy` — força o modo para esta execução.
- `-q, --quiet` — suprime banner de inicialização no stderr.

Em dev, rode direto:
```bash
.venv/bin/python python-backend/cli.py audiencia.txt
```

## Configuração

- `python-backend/config/deny_list.json` — termos que nunca devem ser mascarados, separados por entidade.
- `python-backend/config/context_words.json` — palavras de contexto que elevam o score de cada tipo de documento.

Ambos podem ser editados sem rebuild; o servidor recarrega ao chamar
`POST /config/deny-list` ou ao reiniciar.

## Licença

MIT.
