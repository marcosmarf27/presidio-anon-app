"""
Carrega deny list e palavras de contexto de arquivos JSON externos.
Permite customização sem editar código fonte.
"""

import json
import unicodedata
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent / "config"
_DENY_LIST_FILE = _CONFIG_DIR / "deny_list.json"
_CONTEXT_FILE = _CONFIG_DIR / "context_words.json"


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Normaliza texto para comparação: lowercase + sem acentos + strip."""
    return _strip_accents(text.strip().lower())


def load_deny_list() -> dict[str, set[str]]:
    """
    Retorna dict {entity_type: set(normalized_strings)}.
    Normaliza cada entrada para matching robusto.
    """
    with _DENY_LIST_FILE.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {
        entity: {normalize(term) for term in terms}
        for entity, terms in raw.items()
    }


def load_context_words() -> dict[str, list[str]]:
    """Retorna dict {entity_type: list(context_words)}."""
    with _CONTEXT_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_deny_list(deny_list: dict[str, list[str]]) -> None:
    """Grava deny list no disco (usado pelo endpoint de config)."""
    _DENY_LIST_FILE.write_text(
        json.dumps(deny_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_raw_deny_list() -> dict[str, list[str]]:
    """Retorna o conteúdo bruto do arquivo (para o endpoint GET /config)."""
    with _DENY_LIST_FILE.open(encoding="utf-8") as f:
        return json.load(f)
