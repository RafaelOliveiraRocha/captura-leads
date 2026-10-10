"""Tela da demonstração: apenas localhost, arquivos fictícios e biblioteca padrão."""

import argparse
import html
import secrets
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, urlsplit

from extracao import ler_perfil
from fontes import BASE_DEMO, buscar_perfis
from tratamento import deduplicar, gerar_csv, preparar_resultado

COLUNAS_TELA = ("NOME", "PERFIL", "PUBLICAÇÕES", "SEGUIDORES", "BIO", "LINK", "CONTATO", "ESTADO")


def pesquisar(segmento, cidade, bairro="", base=BASE_DEMO):
    candidatos = buscar_perfis(segmento, cidade, bairro, base)
    return deduplicar(preparar_resultado(item, ler_perfil(item), "Fictícia — HTML local")
                      for item in candidatos)


def criar_servidor(porta=8000, base=BASE_DEMO):
    base = Path(base)
    template = Template((base / "tela.html").read_text(encoding="utf-8"))
    estilo = (base / "style.css").read_bytes()
    downloads = OrderedDict()
    lock = threading.Lock()

    class Tela(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def responder(self, status, conteudo, tipo="text/html; charset=utf-8", download=False):
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(conteudo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'self'; form-action 'self'; base-uri 'none'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="leads-sinteticos.csv"')
            self.end_headers()
            self.wfile.write(conteudo)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/static/style.css":
                self.responder(200, estilo, "text/css; charset=utf-8")
                return
            if url.path not in ("/", "/pesquisar", "/download.csv"):
                self.responder(404, b"Recurso inexistente.", "text/plain; charset=utf-8")
                return
            try:
                query = parse_qs(url.query, max_num_fields=8)
            except ValueError:
                self.responder(400, "Consulta incompatível.".encode("utf-8"), "text/plain; charset=utf-8")
                return
            if url.path == "/download.csv":
                with lock:
                    conteudo = downloads.get(query.get("id", [""])[0])
                if conteudo is None:
                    self.responder(410, "Refaça a pesquisa para gerar o CSV.".encode(),
                                   "text/plain; charset=utf-8")
                else:
                    self.responder(200, conteudo, "text/csv; charset=utf-8", download=True)
                return
            filtros = {campo: query.get(campo, [""])[0] for campo in ("segmento", "cidade", "bairro")}
            linhas, download, status = [], "", 200
            mensagem = "Informe o segmento e a cidade para pesquisar a base fictícia."
            if url.path == "/pesquisar":
                try:
                    linhas = pesquisar(**filtros, base=base)
                    conteudo = gerar_csv(linhas).encode("utf-8")
                    token = secrets.token_urlsafe(18)
                    with lock:
                        downloads[token] = conteudo
                        if len(downloads) > 64:
                            downloads.popitem(last=False)
                    download = f'<a class="botao secundario" href="/download.csv?id={token}">Baixar CSV</a>'
                    mensagem = (f"{len(linhas)} perfis fictícios encontrados."
                                if linhas else "Nenhum perfil fictício corresponde aos filtros.")
                except ValueError as erro:
                    mensagem, status = str(erro), 400
                except (OSError, KeyError, TypeError):
                    mensagem, status = "Não foi possível ler as páginas da demonstração.", 500
            cabecalho = "".join(f"<th>{html.escape(campo)}</th>" for campo in COLUNAS_TELA)
            corpo = "".join('<tr data-perfil="sintetico">' + "".join(
                f"<td>{html.escape(linha[campo])}</td>" for campo in COLUNAS_TELA) + "</tr>"
                for linha in linhas)
            pagina = template.substitute(
                **{campo: html.escape(valor, quote=True) for campo, valor in filtros.items()},
                mensagem=html.escape(mensagem), cabecalho=cabecalho, corpo=corpo, download=download)
            self.responder(status, pagina.encode("utf-8"))

    return ThreadingHTTPServer(("127.0.0.1", porta), Tela)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pesquisa local com perfis e páginas fictícios.")
    parser.add_argument("--porta", type=int, default=8000, help="Porta local (padrão: 8000).")
    args = parser.parse_args(argv)
    if not 1 <= args.porta <= 65535:
        parser.error("Use uma porta de 1 a 65535.")
    try:
        with criar_servidor(args.porta) as servidor:
            print(f"Demonstração fictícia: http://127.0.0.1:{args.porta}", flush=True)
            servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    except OSError:
        parser.exit(1, "Não foi possível abrir a porta local. Escolha outra com --porta.\n")


if __name__ == "__main__":
    main()
