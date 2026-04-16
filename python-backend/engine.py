"""
Engine singleton que inicializa o Presidio AnalyzerEngine + AnonymizerEngine
com suporte a pt-BR.

NLP backend:
  - PRESIDIO_NLP_MODE=transformer (default): usa pierreguillou/ner-bert-large-cased-pt-lenerbr,
    modelo BERT fine-tuned em jurisprudência brasileira (F1≈0.91 em LeNER-Br).
  - PRESIDIO_NLP_MODE=spacy: fallback para pt_core_news_lg (mais leve,
    qualidade inferior em textos jurídicos).
"""

import os
import re

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from recognizers import criar_recognizers_brasil
from mask_config import apply_mask
from config_loader import load_deny_list, normalize

_instance: "PresidioEngine | None" = None

# Regex para detectar sequências de 2+ palavras ALL CAPS (prováveis nomes).
# Só é aplicado no modo spacy — o BERT jurídico não precisa desse truque.
_RE_CAPS_SEQUENCE = re.compile(
    r"\b[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]{2,}"
    r"(?:(?:\s+(?:DE|DA|DO|DOS|DAS|E|DI|DEL|VON)\s+|\s+)"
    r"[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]{2,})+"
    r"\b"
)

# Estende PERSON para a direita quando termina antes de preposição + sobrenome.
# Ex: "Danger Pereira" → "Danger Pereira De Araujo".
_RE_NAME_CONTINUATION_RIGHT = re.compile(
    r"\s+(?:DE|DA|DO|DOS|DAS|E|DI|DEL|VON|De|Da|Do|Dos|Das|Di|Del|Von|de|da|do|dos|das|e|di|del|von)\s+"
    r"[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ]+"
)

# Estende PERSON para a esquerda quando spaCy pegou só o último token.
# Captura "João da " em "João da Silva" quando NER marcou apenas "Silva".
_RE_NAME_CONTINUATION_LEFT = re.compile(
    r"(?:[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ]+\s+"
    r"(?:DE|DA|DO|DOS|DAS|E|DI|DEL|VON|De|Da|Do|Dos|Das|Di|Del|Von|de|da|do|dos|das|e|di|del|von)\s+)+$"
)

# Palavras que não podem iniciar um sobrenome — interrompe a extensão à direita.
_STOP_WORDS_NAME_EXT = {
    "audiencia", "audiência", "processo", "pena", "prisao", "prisão",
    "cumprimento", "medida", "direito", "acordo", "termo", "tutela",
    "instancia", "instância", "origem", "defesa", "acusacao", "acusação",
    "sentenca", "sentença",
}


def _spacy_config() -> dict:
    return {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pt", "model_name": "pt_core_news_lg"}],
    }


def _transformer_config() -> dict:
    return {
        "nlp_engine_name": "transformers",
        "models": [
            {
                "lang_code": "pt",
                "model_name": {
                    "spacy": "pt_core_news_lg",
                    "transformers": "pierreguillou/ner-bert-large-cased-pt-lenerbr",
                },
            }
        ],
        "ner_model_configuration": {
            "labels_to_ignore": ["O"],
            "aggregation_strategy": "max",
            "alignment_mode": "expand",
            "model_to_presidio_entity_mapping": {
                "PESSOA": "PERSON",
                "PER": "PERSON",
                "ORGANIZACAO": "ORGANIZATION",
                "ORG": "ORGANIZATION",
                "LOCAL": "LOCATION",
                "LOC": "LOCATION",
                "TEMPO": "DATE_TIME",
                "TIME": "DATE_TIME",
                "LEGISLACAO": "LAW",
                "JURISPRUDENCIA": "CASE_LAW",
            },
            "low_confidence_score_multiplier": 0.4,
            "low_score_entity_names": ["ORGANIZATION", "ORG"],
        },
    }


class PresidioEngine:
    def __init__(self):
        self._analyzer: AnalyzerEngine | None = None
        self._anonymizer: AnonymizerEngine | None = None
        self._ready = False
        self._nlp_mode = os.environ.get("PRESIDIO_NLP_MODE", "transformer").lower()
        self._deny_list: dict[str, set[str]] = {}

    @property
    def nlp_mode(self) -> str:
        return self._nlp_mode

    def initialize(self):
        """Carrega modelo NLP e inicializa os engines. Chamado uma vez."""
        if self._ready:
            return

        nlp_engine = None
        if self._nlp_mode == "transformer":
            try:
                import transformers  # noqa: F401
                import torch  # noqa: F401
                provider = NlpEngineProvider(nlp_configuration=_transformer_config())
                nlp_engine = provider.create_engine()
            except Exception as exc:
                print(
                    f"[engine] Falha ao carregar modo transformer ({exc!r}). "
                    "Caindo para spaCy.",
                    flush=True,
                )
                self._nlp_mode = "spacy"

        if nlp_engine is None:
            provider = NlpEngineProvider(nlp_configuration=_spacy_config())
            nlp_engine = provider.create_engine()

        registry = RecognizerRegistry(supported_languages=["pt"])
        registry.load_predefined_recognizers(
            nlp_engine=nlp_engine, languages=["pt"]
        )
        for recognizer in criar_recognizers_brasil():
            registry.add_recognizer(recognizer)

        self._analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=nlp_engine,
            supported_languages=["pt"],
        )
        self._anonymizer = AnonymizerEngine()
        self._deny_list = load_deny_list()
        self._ready = True

    def reload_deny_list(self) -> None:
        """Recarrega a deny list do disco (usado pelo endpoint /config)."""
        self._deny_list = load_deny_list()

    def is_ready(self) -> bool:
        return self._ready

    def anonymize(
        self,
        text: str,
        entities: list[str],
        language: str = "pt",
    ) -> dict:
        """
        Analisa e anonimiza o texto, processando parágrafo por parágrafo
        para evitar o limite de 1M chars do spaCy e permitir progresso granular.

        Retorna dict com:
          - anonymized_text: texto com PII mascarado
          - entities_found: lista de entidades detectadas
        """
        if not self._ready or self._analyzer is None or self._anonymizer is None:
            raise RuntimeError("Engine não inicializado. Chame initialize() primeiro.")

        paragraphs = text.split("\n")
        anonymized_paragraphs = []
        all_entities = []
        offset = 0  # Para ajustar posições globais das entidades

        for paragraph in paragraphs:
            if not paragraph.strip():
                anonymized_paragraphs.append(paragraph)
                offset += len(paragraph) + 1  # +1 para o \n
                continue

            # No modo spacy, converte ALL CAPS → Title Case para que o NER
            # CNN reconheça. O BERT jurídico não precisa desse pré-processo.
            if self._nlp_mode == "spacy":
                preprocessed = _RE_CAPS_SEQUENCE.sub(
                    lambda m: m.group(0).title(), paragraph
                )
            else:
                preprocessed = paragraph

            results = self._analyzer.analyze(
                text=preprocessed,
                language=language,
                entities=entities if entities else None,
                score_threshold=0.35,
            )

            if not results:
                anonymized_paragraphs.append(paragraph)
                offset += len(paragraph) + 1
                continue

            if entities:
                results = [r for r in results if r.entity_type in entities]

            adjusted = []
            for r in results:
                txt = preprocessed[r.start:r.end]
                start, end = r.start, r.end

                while start < end and not txt[0].isalpha() and not txt[0].isdigit():
                    start += 1
                    txt = txt[1:]
                while end > start and not txt[-1].isalpha() and not txt[-1].isdigit():
                    end -= 1
                    txt = txt[:-1]

                if start < end and len(txt.strip()) > 1:
                    r.start = start
                    r.end = end
                    adjusted.append(r)

            for r in adjusted:
                if r.entity_type == "PERSON":
                    self._extend_person(preprocessed, r)

            results = self._apply_deny_list(preprocessed, adjusted)

            for r in results:
                all_entities.append({
                    "type": r.entity_type,
                    "text": paragraph[r.start:r.end],
                    "start": r.start + offset,
                    "end": r.end + offset,
                    "score": round(r.score, 2),
                })

            anonymized_paragraph = self._apply_masks_individually(
                paragraph, results
            )
            anonymized_paragraphs.append(anonymized_paragraph)
            offset += len(paragraph) + 1

        return {
            "anonymized_text": "\n".join(anonymized_paragraphs),
            "entities_found": all_entities,
        }

    def _apply_deny_list(self, text: str, results: list) -> list:
        """
        Aplica a deny list a cada entidade detectada:
          - match exato (normalizado) → descarta.
          - detecção começa com termo da deny list + espaço → trimma o prefixo
            institucional (ex: 'Ministério Público Dr. FULANO' → 'FULANO').
          - detecção é prefixo de um termo da deny list → descarta.
        """
        out = []
        for r in results:
            terms = self._deny_list.get(r.entity_type, set())
            detected = text[r.start:r.end]
            norm = normalize(detected)

            if norm in terms:
                continue

            # Prefixo institucional: trimma e mantém só a cauda (ex.: nome real)
            trimmed = False
            for term in terms:
                if not term:
                    continue
                if norm.startswith(term + " "):
                    words_in_term = len(term.split())
                    detected_words = detected.split()
                    if len(detected_words) <= words_in_term:
                        continue
                    tail = " ".join(detected_words[words_in_term:])
                    tail_start_in_detected = detected.find(tail)
                    if tail_start_in_detected > 0:
                        r.start += tail_start_in_detected
                        trimmed = True
                        break

            if trimmed:
                new_detected = text[r.start:r.end]
                if normalize(new_detected) in terms or len(new_detected.strip()) <= 1:
                    continue
                out.append(r)
                continue

            out.append(r)
        return out

    def _extend_person(self, text: str, r) -> None:
        """Estende PERSON à direita e à esquerda para capturar sobrenomes."""
        # Direita: "Danger Pereira" → "Danger Pereira De Araujo"
        remaining = text[r.end:]
        m = _RE_NAME_CONTINUATION_RIGHT.match(remaining)
        while m:
            added = m.group(0)
            # Interrompe se a palavra seguinte for stop-word (ex.: "de audiência")
            next_word = added.strip().split()[-1]
            if normalize(next_word) in _STOP_WORDS_NAME_EXT:
                break
            r.end += m.end()
            remaining = text[r.end:]
            m = _RE_NAME_CONTINUATION_RIGHT.match(remaining)

        # Esquerda: "Silva" com "João da " antes → "João da Silva"
        prefix_region = text[:r.start]
        m_left = _RE_NAME_CONTINUATION_LEFT.search(prefix_region)
        if m_left:
            r.start = m_left.start()

    def _apply_masks_individually(
        self, text: str, results: list
    ) -> str:
        """
        Aplica masks individualmente para cada ocorrência,
        processando de trás para frente para manter as posições corretas.
        """
        sorted_results = sorted(results, key=lambda r: r.start, reverse=True)

        masked_text = text
        for r in sorted_results:
            original = text[r.start:r.end]
            masked = apply_mask(r.entity_type, original)
            masked_text = masked_text[:r.start] + masked + masked_text[r.end:]

        return masked_text


def get_engine() -> PresidioEngine:
    """Retorna a instância singleton do engine."""
    global _instance
    if _instance is None:
        _instance = PresidioEngine()
    return _instance
