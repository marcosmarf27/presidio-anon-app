<p align="center">
  <img src="assets/logo.jpg" alt="Presidio Anon" width="180" />
</p>

<h1 align="center">Presidio Anon</h1>

<p align="center">
  <strong>Anonimizador desktop de PII para textos jurídicos brasileiros.</strong><br/>
  100% local · LGPD-friendly · feito para quem mexe com processo judicial todo dia.
</p>

<p align="center">
  <a href="https://github.com/marcosmarf27/presidio-anon-app/releases/latest"><img src="https://img.shields.io/badge/download-Windows%20x64-0066cc?style=for-the-badge&logo=windows" alt="Download" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge" alt="MIT" /></a>
  <img src="https://img.shields.io/badge/grátis-para%20sempre-ff4081?style=for-the-badge" alt="Grátis" />
  <img src="https://img.shields.io/badge/open%20source-%E2%9D%A4-red?style=for-the-badge" alt="Open Source" />
</p>

<p align="center">
  <img src="assets/hero.jpg" alt="Anonimização de documentos jurídicos" width="100%" />
</p>

## 💚 Grátis, livre e para todo mundo

Este projeto é **open source sob licença MIT**. Você pode:

- ✅ **Baixar e usar** gratuitamente, para sempre — no trabalho, no escritório, em casa.
- ✅ **Alterar o código** como quiser, adaptar para o seu tribunal/vara/escritório.
- ✅ **Redistribuir**, até mesmo comercialmente, desde que mantenha o aviso de licença.
- ✅ **Compartilhar** com colegas que lidam com dados sensíveis — quanto mais gente usando anonimização local, melhor.

Sem cadastro, sem assinatura, sem telemetria, sem pagar nada em momento nenhum.
Se ajudar seu dia a dia, deixe uma ⭐ no repositório — é o único "pagamento" que o projeto aceita.

## Por que existe

Ferramentas genéricas de anonimização erram muito em textos jurídicos: perdem
nomes escritos em CAIXA ALTA, marcam "Ministério Público" como pessoa, não
entendem número CNJ, não validam CPF. O resultado é vazamento de dados ou
mascaramento excessivo que inutiliza o documento.

O Presidio Anon foi montado com o **contexto certo para o tribunal brasileiro**:
modelo NER treinado em jurisprudência, regex dos documentos oficiais com
**validação de dígito verificador**, e deny list de expressões jurídicas que
nenhum servidor, advogado ou magistrado quer ver mascarada.

## Diferenciais

### 🎯 NER jurídico brasileiro de fato
Usa [`pierreguillou/ner-bert-large-cased-pt-lenerbr`](https://huggingface.co/pierreguillou/ner-bert-large-cased-pt-lenerbr) — BERT fine-tuned no
dataset **LeNER-Br** (jurisprudência real de vários tribunais BR), F1 ≈ 0.91.
Reconhece nomes em `CAIXA ALTA`, `Title Case` e `minúsculas` sem gambiarra de
pré-processamento, além de entidades específicas como `LEGISLAÇÃO` e
`JURISPRUDÊNCIA`.

### 🔢 Documentos BR com validação de checksum
Não é só regex. CPF, CNPJ, PIS/NIT e número de processo CNJ passam pelo
**dígito verificador**. Candidato com DV inválido (ex: `00000000000`) é
**descartado**; candidato válido tem o score **elevado** para 0.95+. Efeito:
menos falso positivo, mais recall em variações como CPF sem formatação.

### 🧠 Deny list jurídica acoplada
Termos como `Ministério Público`, `Tribunal de Justiça`, `Caixa Econômica`,
`Banco do Brasil`, `Código de Processo Penal`, `Juíza de Direito`, etc.
**não** são mascarados — mesmo quando o modelo insiste em classificá-los
como pessoa/local. Configurável via `config/deny_list.json` sem recompilar.

### 💻 Interface que respeita o fluxo do operador
- **Arraste e solte** múltiplos arquivos (até 10) — `.txt`, `.md`, `.rtf`.
- **Histórico local** em localStorage: abra resultados anteriores com 1 clique.
- **Preview side-by-side** com highlight das entidades detectadas.
- **Um botão de salvar** grava `nome_anonimizado.txt` ao lado do original.
- **Toggle de entidades**: escolha mascarar só CPF, ou só nomes, ou tudo.

### ⌨️ CLI nativa (Windows + WSL)
Além da GUI, a tela **Linha de Comando** instala automaticamente o comando
`presidio-anon` no `cmd` / `PowerShell` (via User PATH) e no **WSL bash**
(shim em `~/.local/bin` via interop). Uma instalação, dois ambientes — perfeito
para automação, scripts de lote e agentes como Claude Code:

```bash
presidio-anon processo.txt -o processo_anon.txt
cat peticao.txt | presidio-anon --entities PERSON,CPF_BR
presidio-anon autos/*.txt --in-place
presidio-anon termo.txt -q --format json   # para agentes/pipelines
```

### 🔒 Zero envio de dados
Tudo roda como processo local na sua máquina. Nenhuma chamada para serviço
externo no caminho da anonimização. O modelo BERT é baixado apenas **uma vez**
(HuggingFace) na primeira execução; depois disso, offline.

## 📥 Baixar

**Windows (10/11 x64):**
👉 **[Baixar `Presidio Anon Setup.exe` (último release)](https://github.com/marcosmarf27/presidio-anon-app/releases/latest)**

O instalador tem ~660 MB porque já traz Python embutido + `transformers` +
`torch` CPU. Na primeira execução baixa o modelo BERT (~1.7 GB) — requer
internet só nesse momento. Depois funciona 100% offline.

Linux/Mac: rode em modo dev (abaixo). Build nativo sob demanda.

## Entidades reconhecidas

| Tipo | Exemplo | Técnica |
|---|---|---|
| `PERSON` | nomes próprios | NER BERT + regex de fallback |
| `CPF_BR` | `123.456.789-09`, `12345678909` | regex + DV |
| `CNPJ_BR` | `12.345.678/0001-90`, `12345678000190` | regex + DV |
| `RG_BR` | `12.345.678-9` | regex |
| `NIT_PIS_PASEP` | `120.45678.90-0` | regex + DV |
| `NUMERO_PROCESSO_CNJ` | `0001234-56.2023.8.06.0001` | regex + checksum CNJ |
| `OAB_BR` | `OAB/CE 45.678` | regex |
| `PHONE_NUMBER_BR` | `(85) 99876-5432`, `+55 85…` | regex |
| `EMAIL_ADDRESS` | `joao@exemplo.com` | regex padrão Presidio |
| `LOCATION` | endereços, cidades | NER BERT |
| `DATE_OF_BIRTH` | `15/03/1985` | regex + contexto |
| `CONTA_BANCARIA` | `Ag 1234 CC 56789-0` | regex |

Cada entidade tem uma **máscara própria** que preserva parte do valor para
auditoria (ex: `CPF 123.***.***-09`, `nome J*** d* S****`) — configurável em
`python-backend/mask_config.py`.

## Stack

- **Desktop**: Electron 41 + React 19 + TypeScript + Tailwind.
- **Backend**: FastAPI + [Microsoft Presidio](https://microsoft.github.io/presidio/).
- **NER default**: BERT fine-tuned LeNER-Br (F1 ≈ 0.91).
- **NER fallback**: `pt_core_news_lg` (modo `PRESIDIO_NLP_MODE=spacy`).

## Rodar em desenvolvimento

Pré-requisitos: Node 20+, Python 3.12.

```bash
npm install

python3 -m venv .venv
.venv/bin/pip install -r python-backend/requirements.txt
.venv/bin/python -m spacy download pt_core_news_lg

npm run dev:electron
```

Para usar o modo leve (sem baixar BERT):
```bash
PRESIDIO_NLP_MODE=spacy npm run dev:electron
```

## Testes

```bash
.venv/bin/pytest python-backend/tests -v
```

Mede recall e precisão sobre fixture jurídica **sintética** (sem dados reais).
Ver `python-backend/tests/fixtures/`.

## Configuração por JSON (sem recompilar)

- `python-backend/config/deny_list.json` — termos que **nunca** devem ser
  mascarados, separados por tipo (`PERSON`, `LOCATION`, `ORGANIZATION`).
- `python-backend/config/context_words.json` — palavras que, quando próximas
  de um candidato regex, **elevam** o score (ex: `cpf`, `processo`, `oab`).

Edite, salve, reinicie o app — ou chame `POST /config/deny-list` para recarga a quente.

## Licença

MIT.
