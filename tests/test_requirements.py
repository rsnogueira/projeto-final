"""O requirements.txt reflete as dependências realmente usadas, com as versões instaladas no .venv."""

import ast
import re
import sys
from importlib.metadata import packages_distributions, version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOCAIS = {"orcamento_pecas", "tests", "conftest"}


def _normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _requisitos() -> dict[str, tuple[str, str]]:
    """nome normalizado -> (versão fixada, comentário da linha)."""
    requisitos = {}
    for linha in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines():
        conteudo, _, comentario = linha.partition("#")
        conteudo = conteudo.strip()
        if not conteudo:
            continue
        nome, sep, versao = conteudo.partition("==")
        assert sep, f"versão não fixada com '==': {linha!r}"
        requisitos[_normalizar(nome.strip())] = (versao.strip(), comentario.strip())
    return requisitos


def _distribuicoes_importadas() -> set[str]:
    modulos: set[str] = set()
    for pasta in ("orcamento_pecas", "tests"):
        for arquivo in (RAIZ / pasta).rglob("*.py"):
            for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
                if isinstance(no, ast.Import):
                    modulos.update(alias.name.split(".")[0] for alias in no.names)
                elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
                    modulos.add(no.module.split(".")[0])
    terceiros = {m for m in modulos if m not in sys.stdlib_module_names and m not in LOCAIS}
    mapa = packages_distributions()
    sem_distribuicao = sorted(m for m in terceiros if m not in mapa)
    assert not sem_distribuicao, f"módulos importados sem distribuição instalada: {sem_distribuicao}"
    return {_normalizar(d) for m in terceiros for d in mapa[m]}


def test_todo_import_de_terceiros_esta_no_requirements():
    faltando = _distribuicoes_importadas() - set(_requisitos())
    assert not faltando, f"importados mas ausentes do requirements.txt: {sorted(faltando)}"


def test_requirements_nao_tem_pacote_sem_uso():
    importados = _distribuicoes_importadas()
    sem_uso = {
        nome for nome, (_, comentario) in _requisitos().items()
        if nome not in importados and not comentario.lower().startswith("indireto:")
    }
    assert not sem_uso, f"no requirements.txt sem import nem justificativa 'indireto:': {sorted(sem_uso)}"


def test_versoes_fixadas_sao_as_instaladas():
    divergentes = {nome: (fixada, version(nome)) for nome, (fixada, _) in _requisitos().items() if version(nome) != fixada}
    assert not divergentes, f"versão fixada × instalada: {divergentes}"
