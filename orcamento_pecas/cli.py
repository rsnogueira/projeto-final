"""Interface de linha de comando: `python -m orcamento_pecas {servidor|auditoria|revisao}`."""

import argparse
import os
import sys
from pathlib import Path

from orcamento_pecas.config import VARIAVEL_AMBIENTE_BANCO, caminho_banco


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m orcamento_pecas", description="API de consulta para orçamento de peças (v1).")
    sub = parser.add_subparsers(dest="comando", required=True)

    servidor = sub.add_parser("servidor", help="sobe a API (Swagger em /docs)")
    servidor.add_argument("--host", default="127.0.0.1")
    servidor.add_argument("--port", type=int, default=8000)
    servidor.add_argument("--banco", help="caminho do SQLite (padrão: Database/SQLite/db_proj_final.db)")
    servidor.add_argument("--reload", action="store_true", help="recarrega ao alterar o código (desenvolvimento)")

    auditoria = sub.add_parser("auditoria", help="audita a base e as respostas; gera JSON e Excel")
    auditoria.add_argument("--banco", help="caminho do SQLite (padrão: Database/SQLite/db_proj_final.db)")
    auditoria.add_argument("--amostra", type=int, default=30, help="tamanho da amostra para revisão manual")
    auditoria.add_argument("--semente", type=int, default=42, help="semente do sorteio da amostra")
    auditoria.add_argument("--saida", default="saidas/auditoria", help="pasta dos relatórios")

    revisao = sub.add_parser("revisao", help="resume a revisão manual preenchida no Excel da auditoria")
    revisao.add_argument("arquivo", help="planilha .xlsx gerada pela auditoria")
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    args = _parser().parse_args(argumentos)

    if args.comando == "servidor":
        import uvicorn

        if args.banco:
            os.environ[VARIAVEL_AMBIENTE_BANCO] = str(args.banco)
        uvicorn.run("orcamento_pecas.api.app:criar_app", factory=True, host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.comando == "auditoria":
        from orcamento_pecas.auditoria.executor import executar_auditoria
        from orcamento_pecas.dados.conexao import BancoIndisponivelError

        try:
            relatorio, caminho_json, caminho_excel = executar_auditoria(
                caminho_banco(args.banco), args.amostra, args.semente, Path(args.saida),
                comando=" ".join(["python -m orcamento_pecas", *argumentos]),
            )
        except BancoIndisponivelError as erro:
            print(erro, file=sys.stderr)
            return 2
        resumo = relatorio.resumo
        print(f"JSON:  {caminho_json}")
        print(f"Excel: {caminho_excel}")
        print(f"consultas executadas: {resumo.consultas_executadas}")
        print(f"valores verificados: {resumo.valores_verificados}")
        print(f"falhas: {resumo.falhas} {resumo.falhas_por_invariante or ''}".rstrip())
        print(f"alertas da base: {resumo.alertas_base_por_codigo}")
        print(f"amostra: {resumo.itens_amostra} itens (semente {args.semente})")
        return 1 if resumo.falhas else 0

    from orcamento_pecas.auditoria.relatorio import ler_revisao

    resumo_revisao = ler_revisao(Path(args.arquivo))
    print(resumo_revisao.model_dump_json(indent=2))
    return 1 if resumo_revisao.divergencias or resumo_revisao.invalidos else 0
