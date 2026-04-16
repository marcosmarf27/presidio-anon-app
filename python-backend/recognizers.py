"""
PatternRecognizers customizados para entidades brasileiras.
Cada recognizer detecta um tipo de PII via regex + contexto.
Recognizers de documentos usam dígito verificador para eliminar falsos
positivos e elevar o score de candidatos confirmados.
"""

from __future__ import annotations

from typing import Callable, Optional

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

from config_loader import load_context_words
from validators import (
    cnpj_valid,
    cpf_valid,
    pis_valid,
    processo_cnj_valid,
)


class ValidatingPatternRecognizer(PatternRecognizer):
    """
    PatternRecognizer que usa uma função de validação de dígito verificador
    para descartar candidatos inválidos e elevar o score dos válidos.

    - Se o candidato tem DV válido → score é elevado para `boosted_score`.
    - Se o candidato tem DV inválido → resultado é descartado.
    - Padrões com dv_required=False são deixados como estão (útil para
      formatos canônicos onde o regex já é bastante específico).
    """

    def __init__(
        self,
        supported_entity: str,
        patterns: list[Pattern],
        context: list[str],
        validator: Callable[[str], bool],
        boosted_score: float = 0.95,
        dv_required_patterns: Optional[set[str]] = None,
        supported_language: str = "pt",
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )
        self._validator = validator
        self._boosted_score = boosted_score
        self._dv_required = dv_required_patterns or set()

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
        regex_flags: Optional[int] = None,
    ) -> list[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts, regex_flags)
        if not results:
            return results

        filtered: list[RecognizerResult] = []
        for r in results:
            candidate = text[r.start:r.end]
            is_valid = self._validator(candidate)

            pattern_name = (
                r.analysis_explanation.pattern_name
                if r.analysis_explanation is not None
                else ""
            )

            if is_valid:
                r.score = max(r.score, self._boosted_score)
                filtered.append(r)
            elif pattern_name in self._dv_required:
                # Regex pediu DV e candidato falhou — descarta.
                continue
            else:
                # Formato canônico bastante específico: mantém score base.
                filtered.append(r)

        return filtered


def criar_recognizers_brasil() -> list[PatternRecognizer]:
    """Retorna lista de recognizers para entidades brasileiras."""

    ctx = load_context_words()

    # --- CPF ---
    # Padrão formatado: confia no formato + eleva com DV.
    # Padrão cru (11 dígitos): exige DV válido + contexto próximo (o Presidio
    # elevará o score via ContextAwareEnhancer se houver palavras como "cpf").
    cpf = ValidatingPatternRecognizer(
        supported_entity="CPF_BR",
        patterns=[
            Pattern("cpf_fmt", r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", 0.6),
            Pattern("cpf_raw", r"(?<!\d)\d{11}(?!\d)", 0.3),
        ],
        context=ctx["CPF_BR"],
        validator=cpf_valid,
        boosted_score=0.95,
        dv_required_patterns={"cpf_raw"},
    )

    # --- CNPJ ---
    cnpj = ValidatingPatternRecognizer(
        supported_entity="CNPJ_BR",
        patterns=[
            Pattern("cnpj_fmt", r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", 0.6),
            Pattern("cnpj_raw", r"(?<!\d)\d{14}(?!\d)", 0.3),
        ],
        context=ctx["CNPJ_BR"],
        validator=cnpj_valid,
        boosted_score=0.95,
        dv_required_patterns={"cnpj_raw"},
    )

    # --- RG ---
    # RG não tem algoritmo universal de DV (cada UF é diferente), então não
    # validamos; apenas ampliamos o regex para cobrir variações comuns.
    rg = PatternRecognizer(
        supported_entity="RG_BR",
        patterns=[
            Pattern("rg_fmt", r"\b\d{1,2}\.\d{3}\.\d{3}-[\dxX]\b", 0.7),
            Pattern("rg_sem_ponto", r"(?<!\d)\d{7,9}(?!\d)", 0.25),
        ],
        supported_language="pt",
        context=ctx["RG_BR"],
    )

    # --- Telefone brasileiro ---
    # Inclui formato internacional +55, DDD entre parênteses, formato com
    # hífen, e variante colada sem separador (11 dígitos ou 10 dígitos).
    telefone = PatternRecognizer(
        supported_entity="PHONE_NUMBER_BR",
        patterns=[
            Pattern(
                "tel_br_intl",
                r"\+55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b",
                0.85,
            ),
            Pattern(
                "tel_br_parenteses",
                r"\(\d{2}\)\s?\d{4,5}-?\d{4}\b",
                0.8,
            ),
            Pattern(
                "tel_br_hifen",
                r"\b\d{2}\s?\d{4,5}-\d{4}\b",
                0.7,
            ),
        ],
        supported_language="pt",
        context=ctx["PHONE_NUMBER_BR"],
    )

    # --- OAB ---
    # Aceita "OAB/CE 12345", "OAB CE 12345", "OAB nº 12345", "OAB/CE 12.345".
    oab = PatternRecognizer(
        supported_entity="OAB_BR",
        patterns=[
            Pattern(
                "oab_estado",
                r"\bOAB\s*[/\-]?\s*[A-Z]{2}\s*[/\-:]?\s*n?º?\.?\s*\d[\d.]{3,7}\b",
                0.9,
            ),
            Pattern(
                "oab_generico",
                r"\bOAB[/\s]?\w{2}[/\s]?\d[\d.]{3,7}\b",
                0.85,
            ),
        ],
        supported_language="pt",
        context=ctx["OAB_BR"],
    )

    # --- Data de nascimento ---
    data_nascimento = PatternRecognizer(
        supported_entity="DATE_OF_BIRTH",
        patterns=[
            Pattern("data_nasc", r"\b\d{2}/\d{2}/\d{4}\b", 0.4),
        ],
        supported_language="pt",
        context=ctx["DATE_OF_BIRTH"],
    )

    # --- NIT / PIS / PASEP ---
    nit = ValidatingPatternRecognizer(
        supported_entity="NIT_PIS_PASEP",
        patterns=[
            Pattern("nit_fmt", r"\b\d{3}\.\d{5}\.\d{2}-\d\b", 0.6),
            Pattern("nit_raw", r"(?<!\d)\d{11}(?!\d)", 0.3),
        ],
        context=ctx["NIT_PIS_PASEP"],
        validator=pis_valid,
        boosted_score=0.9,
        dv_required_patterns={"nit_raw"},
    )

    # --- Número de processo CNJ ---
    # Formato formatado: NNNNNNN-DD.AAAA.J.TR.OOOO.
    # Formato sem pontuação: 20 dígitos contíguos → exige checksum.
    processo_cnj = ValidatingPatternRecognizer(
        supported_entity="NUMERO_PROCESSO_CNJ",
        patterns=[
            Pattern(
                "processo_cnj_fmt",
                r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b",
                0.75,
            ),
            Pattern(
                "processo_cnj_raw",
                r"(?<!\d)\d{20}(?!\d)",
                0.3,
            ),
        ],
        context=ctx["NUMERO_PROCESSO_CNJ"],
        validator=processo_cnj_valid,
        boosted_score=0.98,
        dv_required_patterns={"processo_cnj_raw"},
    )

    # --- Conta bancária ---
    conta_bancaria = PatternRecognizer(
        supported_entity="CONTA_BANCARIA",
        patterns=[
            Pattern(
                "conta_ag_cc",
                r"\b[Aa]g(?:[êe]ncia)?[:\s]*\d{3,5}[\s,\-]*(?:[Cc](?:onta)?[:\s]*|[Cc]{2}[:\s]*|[Cc][Pp][:\s]*)\d{4,12}-?\d?\b",
                0.75,
            ),
        ],
        supported_language="pt",
        context=ctx["CONTA_BANCARIA"],
    )

    # --- Nomes antes de parênteses: "FULANO DE TAL (ADVOGADO)" ---
    # Mantido como fallback para casos onde o NER perde (raros com BERT,
    # mas ainda úteis para redundância).
    nome_antes_papel = PatternRecognizer(
        supported_entity="PERSON",
        patterns=[
            Pattern(
                "nome_antes_papel",
                r"\b([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ]+(?:\s+(?:DE|DA|DO|DOS|DAS|E|DI|DEL|VON|de|da|do|dos|das|e|di|del|von)?\s*[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑa-záàâãéèêíïóôõöúçñ]+)+)(?=\s*\()",
                0.6,
            ),
        ],
        supported_language="pt",
        context=ctx["PERSON"],
    )

    return [
        cpf, cnpj, rg, telefone, oab,
        data_nascimento, nit, processo_cnj, conta_bancaria,
        nome_antes_papel,
    ]
