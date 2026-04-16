"""
Teste de acurácia de anonimização sobre fixture jurídica sintética.

Mede:
  - Recall: quantas PII esperadas foram mascaradas.
  - Falsos positivos (amostra): quantos termos que não deveriam ser
    mascarados estão intactos.

Roda com o modo NLP definido na env (default: transformer). Para rodar
no modo leve (spaCy), exporte `PRESIDIO_NLP_MODE=spacy` antes do pytest.
"""

import json
from pathlib import Path

import pytest

from engine import get_engine


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def engine():
    eng = get_engine()
    eng.initialize()
    return eng


@pytest.fixture(scope="module")
def fixture_data():
    text = (FIXTURE_DIR / "jurisprudencia_sintetica.txt").read_text(encoding="utf-8")
    expected = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))
    return text, expected


@pytest.fixture(scope="module")
def result(engine, fixture_data):
    text, _ = fixture_data
    return engine.anonymize(text=text, entities=[])


def _count_recall(anonymized: str, expected_pii: dict) -> tuple[int, int, list[str]]:
    total, masked, missing = 0, 0, []
    for _entity, items in expected_pii.items():
        for item in items:
            total += 1
            if item not in anonymized:
                masked += 1
            else:
                missing.append(item)
    return masked, total, missing


def _count_precision(anonymized: str, should_not: list[str]) -> tuple[int, int, list[str]]:
    total, ok, wrongly_masked = len(should_not), 0, []
    for term in should_not:
        if term in anonymized:
            ok += 1
        else:
            wrongly_masked.append(term)
    return ok, total, wrongly_masked


def test_recall(result, fixture_data):
    _, expected = fixture_data
    masked, total, missing = _count_recall(
        result["anonymized_text"], expected["should_be_masked"]
    )
    recall = masked / total if total else 0.0
    print(f"\nRecall: {recall:.2%} ({masked}/{total})")
    if missing:
        print("PII não mascaradas:")
        for m in missing:
            print(f"  - {m!r}")
    assert recall >= 0.85, f"Recall baixo: {recall:.2%}. Faltam: {missing}"


def test_precision_sample(result, fixture_data):
    _, expected = fixture_data
    ok, total, wrongly = _count_precision(
        result["anonymized_text"], expected["should_not_be_masked"]
    )
    precision = ok / total if total else 0.0
    print(f"\nPrecisão (amostra): {precision:.2%} ({ok}/{total})")
    if wrongly:
        print("Termos erroneamente mascarados:")
        for w in wrongly:
            print(f"  - {w!r}")
    assert precision >= 0.80, f"Muitos falsos positivos: {wrongly}"


def test_cpf_invalido_nao_mascara(engine):
    """CPF com DV inválido (sem contexto) não deve ser mascarado."""
    text = "Sequência aleatória de onze dígitos: 11111111111."
    out = engine.anonymize(text=text, entities=["CPF_BR"])
    assert "11111111111" in out["anonymized_text"], (
        "CPF com todos dígitos iguais foi mascarado indevidamente."
    )


def test_cpf_valido_sem_formato_com_contexto(engine):
    """CPF válido sem formatação, com contexto explícito, deve ser mascarado."""
    text = "O autor apresentou o CPF 12345678909 no cadastro."
    out = engine.anonymize(text=text, entities=["CPF_BR"])
    assert "12345678909" not in out["anonymized_text"], (
        "CPF válido com contexto não foi detectado."
    )
