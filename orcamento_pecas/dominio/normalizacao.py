"""Regras determinísticas de normalização. Nunca alteram o valor original: só derivam o normalizado."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from orcamento_pecas.dominio.modelos import Correspondencia, MotorNormalizado

# --- texto ---------------------------------------------------------------------


def normalizar_texto(valor: str | None) -> str | None:
    """Maiúsculas, sem acentos, espaços colapsados. Texto vazio vira None."""
    if valor is None:
        return None
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", str(valor)) if not unicodedata.combining(c))
    texto = " ".join(sem_acento.upper().split())
    return texto or None


_SEPARADOR_SEGMENTOS = re.compile(r"<BR\s*/?>|/")


def segmentos_descricao(descricao: str | None) -> list[str]:
    """Quebra a descrição em `<br>` e `/` (itens que a base junta numa só linha)."""
    texto = normalizar_texto(descricao) or ""
    return [s for s in (p.strip() for p in _SEPARADOR_SEGMENTOS.split(texto)) if s]


def modelos_base(descricao: str | None) -> list[str]:
    """Valor DERIVADO: primeira palavra de cada segmento, sem repetição, na ordem em que aparece."""
    vistos: list[str] = []
    for segmento in segmentos_descricao(descricao):
        primeira = segmento.split()[0]
        if primeira not in vistos:
            vistos.append(primeira)
    return vistos


def corresponde_modelo(descricao: str | None, modelo: str | None) -> Correspondencia | None:
    alvo = normalizar_texto(modelo)
    if not alvo:
        return None
    segmentos = segmentos_descricao(descricao)
    for segmento in segmentos:
        if segmento == alvo or segmento.startswith(alvo + " "):
            return Correspondencia(tipo="inicio_segmento", confianca="alta")
    palavra_inteira = re.compile(rf"(?<!\S){re.escape(alvo)}(?!\S)")
    for segmento in segmentos:
        if palavra_inteira.search(segmento):
            return Correspondencia(tipo="palavra_interna", confianca="baixa")
    return None


# --- anos ----------------------------------------------------------------------


@dataclass(frozen=True)
class FaixaInterpretada:
    inicio: int | None
    fim: int | None
    interpretada: bool


_FAIXA_FECHADA = re.compile(r"^(\d{4})\s*-\s*(\d{4})$")
_FAIXA_FIM_ABERTO = re.compile(r"^(\d{4})\s*-\s*(?:\.\.\.|…|-)?$")
_FAIXA_INICIO_ABERTO = re.compile(r"^(?:\.\.\.|…)\s*-\s*(\d{4})$")


def interpretar_faixa_ano(faixa: str | None) -> FaixaInterpretada:
    """Interpreta `FaixaAno` só para comparar com as colunas de ano (a filtragem usa as colunas)."""
    texto = (faixa or "").strip()
    if m := _FAIXA_FECHADA.match(texto):
        return FaixaInterpretada(int(m.group(1)), int(m.group(2)), True)
    if m := _FAIXA_FIM_ABERTO.match(texto):
        return FaixaInterpretada(int(m.group(1)), None, True)
    if m := _FAIXA_INICIO_ABERTO.match(texto):
        return FaixaInterpretada(None, int(m.group(1)), True)
    return FaixaInterpretada(None, None, False)


def faixa_diverge_das_colunas(faixa: FaixaInterpretada, ano_inicio: int | None, ano_fim: int | None) -> bool:
    if not faixa.interpretada:
        return False
    return faixa.inicio != ano_inicio or faixa.fim != ano_fim


def normalizar_ano_fim(valor: object) -> int | None:
    """Inteiro é mantido; texto de 4 dígitos vira inteiro; vazio, NULL ou outro texto vira None."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and re.fullmatch(r"\d{4}", valor.strip()):
        return int(valor.strip())
    return None


def ano_compativel(ano: int, inicio: int, fim: int | None) -> bool:
    """Bordas inclusivas. Fim ausente (faixa aberta) conta como compatível a partir do início (decisão D2)."""
    return inicio <= ano and (fim is None or ano <= fim)


# --- motorização ---------------------------------------------------------------

_CILINDRADA = re.compile(r"(?<![\d.])(\d\.\d)(?![\d.])\s*L?\b")
_VALVULAS = re.compile(r"\b(\d{1,2})V\b")
_CILINDROS = re.compile(r"\b([LV]\d{1,2})\b")
_COMANDO = re.compile(r"\b(DOHC|SOHC|OHV)\b")
# Palavras genéricas que não são código de motor (ex.: "MOTOR 1.6 16V").
_PALAVRAS_GENERICAS = {"MOTOR"}


def interpretar_motorizacao(texto: str | None) -> MotorNormalizado:
    normal = normalizar_texto(texto) or ""
    normal = normal.replace(" - ", " ")
    normal = re.sub(r"^-\s*", "", normal).strip()

    cilindrada = _CILINDRADA.search(normal)
    if cilindrada is None:
        return MotorNormalizado(
            codigos=[], cilindrada_l=None, valvulas=None, cilindros=None, comando=None,
            interpretada=False, chave=f"TEXTO:{normal}",
        )

    prefixo = normal[: cilindrada.start()]
    resto = normal[cilindrada.end():]
    codigos: list[str] = []
    for parte in prefixo.split("/"):
        palavras = [p for p in parte.split() if p not in _PALAVRAS_GENERICAS]
        if palavras:
            codigos.append(" ".join(palavras))

    valvulas = int(m.group(1)) if (m := _VALVULAS.search(resto)) else None
    cilindros = m.group(1) if (m := _CILINDROS.search(resto)) else None
    comando = m.group(1) if (m := _COMANDO.search(resto)) else None
    chave = "|".join([
        "+".join(codigos) or "?",
        cilindrada.group(1),
        f"{valvulas}V" if valvulas is not None else "?",
        cilindros or "?",
        comando or "?",
    ])
    return MotorNormalizado(
        codigos=codigos, cilindrada_l=cilindrada.group(1), valvulas=valvulas, cilindros=cilindros,
        comando=comando, interpretada=True, chave=chave,
    )


# --- produtos ------------------------------------------------------------------


def normalizar_preco(valor: float | int | None) -> Decimal | None:
    """Decimal exato a partir do texto do número, sem arredondar."""
    if valor is None or isinstance(valor, bool):
        return None
    return Decimal(str(valor))


def numero_produto_base(numero: str) -> str:
    """Número sem o prefixo literal `#NAC_`. Uso exclusivo na detecção de possível duplicidade."""
    texto = numero.strip()
    return texto.removeprefix("#NAC_")
