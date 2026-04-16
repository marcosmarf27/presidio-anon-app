"""
Validação de dígito verificador de documentos brasileiros.
Usado para elevar o score de candidatos regex válidos e descartar falsos
positivos (ex: "00000000000" casa com o padrão de CPF mas não é válido).
"""

import re


_RE_NON_DIGIT = re.compile(r"\D")


def _only_digits(text: str) -> str:
    return _RE_NON_DIGIT.sub("", text)


def _all_same(digits: str) -> bool:
    return len(set(digits)) == 1


def cpf_valid(text: str) -> bool:
    digits = _only_digits(text)
    if len(digits) != 11 or _all_same(digits):
        return False

    for i in (9, 10):
        total = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
        dv = (total * 10) % 11
        if dv == 10:
            dv = 0
        if dv != int(digits[i]):
            return False
    return True


def cnpj_valid(text: str) -> bool:
    digits = _only_digits(text)
    if len(digits) != 14 or _all_same(digits):
        return False

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6] + weights_1

    for weights, pos in ((weights_1, 12), (weights_2, 13)):
        total = sum(int(digits[i]) * weights[i] for i in range(len(weights)))
        dv = total % 11
        dv = 0 if dv < 2 else 11 - dv
        if dv != int(digits[pos]):
            return False
    return True


def pis_valid(text: str) -> bool:
    digits = _only_digits(text)
    if len(digits) != 11 or _all_same(digits):
        return False

    weights = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights[i] for i in range(10))
    dv = total % 11
    dv = 0 if dv < 2 else 11 - dv
    return dv == int(digits[10])


def processo_cnj_valid(text: str) -> bool:
    """
    Validação do DV de número único do CNJ (Res. 65/2008).
    Fórmula: módulo 97 sobre (NNNNNNN AAAA JTR OOOO) * 100 + DD == 1.
    """
    digits = _only_digits(text)
    if len(digits) != 20:
        return False

    sequencial = digits[0:7]
    dv_informado = digits[7:9]
    ano = digits[9:13]
    justica = digits[13]
    tribunal = digits[14:16]
    origem = digits[16:20]

    base = int(sequencial + ano + justica + tribunal + origem)
    dv_calc = 98 - (base * 100) % 97
    return dv_calc == int(dv_informado)
