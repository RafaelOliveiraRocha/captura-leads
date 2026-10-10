import ast
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from app import criar_servidor, pesquisar
from fontes import BASE_DEMO, buscar_perfis
from tratamento import COLUNAS, gerar_csv, salvar_csv

ROOT = Path(__file__).resolve().parents[1]


class Demonstracao(unittest.TestCase):
    def test_filtros_acentos_e_repeticoes(self):
        self.assertEqual(4, len(buscar_perfis("Restaurantes", "São Paulo")))
        self.assertEqual(3, len(pesquisar("RESTAURANTES", "sao PAULO")))
        self.assertEqual(2, len(pesquisar("restaurante", "São Paulo", "IPIRANGA")))
        self.assertEqual(1, len(pesquisar("Restaurantes", "São Paulo", "butanta")))
        self.assertEqual(1, len(pesquisar("Livrarias", "São Paulo")))
        self.assertEqual(1, len(pesquisar("Restaurantes", "Campinas")))
        self.assertEqual([], pesquisar("Oficinas", "São Paulo"))
        with self.assertRaisesRegex(ValueError, "segmento e a cidade"):
            pesquisar("", "São Paulo")

    def test_campos_ausentes_e_textuais(self):
        linhas = pesquisar("Restaurantes", "São Paulo")
        self.assertEqual("0012", linhas[0]["PUBLICAÇÕES"])
        self.assertEqual("1,2 mil", linhas[0]["SEGUIDORES"])
        self.assertEqual("0000", linhas[1]["PUBLICAÇÕES"])
        self.assertEqual("007", linhas[1]["SEGUIDORES"])
        self.assertEqual("", linhas[1]["CONTATO"])
        self.assertEqual("", linhas[1]["LINK"])
        self.assertEqual("Campos ausentes: link, contato.", linhas[1]["ESTADO"])
        self.assertEqual("", linhas[2]["PUBLICAÇÕES"])
        self.assertEqual("", linhas[2]["BIO"])
        self.assertEqual("0030", linhas[2]["SEGUIDORES"])
        self.assertTrue(all(linha["FONTE"] == "Fictícia — HTML local" for linha in linhas))
        self.assertTrue(all(".example.invalid" in linha["PERFIL"] for linha in linhas))

    def test_html_e_realmente_processado(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "demo"
            shutil.copytree(BASE_DEMO, base)
            pagina = base / "perfis/restaurante-a.html"
            pagina.write_text(pagina.read_text().replace("Restaurante Exemplo A", "Outro nome fictício")
                              .replace(">0012<", ">000123<"), encoding="utf-8")
            linha = pesquisar("Restaurantes", "São Paulo", base=base)[0]
            self.assertEqual("Outro nome fictício", linha["NOME"])
            self.assertEqual("000123", linha["PUBLICAÇÕES"])

    def test_csv_referencia_e_entradas_intactas(self):
        antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE_DEMO.rglob("*") if p.is_file()}
        linhas = pesquisar("Restaurantes", "São Paulo")
        texto = gerar_csv(linhas)
        self.assertEqual(linhas, list(csv.DictReader(io.StringIO(texto))))
        self.assertEqual(texto.encode(), (ROOT / "examples/resultado-sintetico.csv").read_bytes())
        vazio = csv.DictReader(io.StringIO(gerar_csv([])))
        self.assertEqual(list(COLUNAS), vazio.fieldnames)
        self.assertEqual([], list(vazio))
        with tempfile.TemporaryDirectory() as temp:
            saida = Path(temp) / "resultado.csv"
            salvar_csv(linhas, saida)
            with self.assertRaises(FileExistsError):
                salvar_csv([], saida)
            self.assertEqual(texto.encode(), saida.read_bytes())
        self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in antes.items()))

    def test_importacao_e_ajuda_sem_automacao(self):
        codigo = r'''
import importlib, importlib.abc, runpy, sys
class Impedir(importlib.abc.MetaPathFinder):
    def find_spec(self, nome, path=None, target=None):
        if nome.split(".")[0] in ("requests", "selenium", "pandas"):
            raise AssertionError("Dependência externa carregada")
def auditoria(evento, args):
    if evento in ("socket.__new__", "socket.connect", "subprocess.Popen", "os.system"):
        raise AssertionError("Efeito externo durante importação ou ajuda")
sys.meta_path.insert(0, Impedir())
sys.addaudithook(auditoria)
for nome in ("app", "cod", "leads", "tratamento", "fontes", "extracao", "externo"):
    importlib.import_module(nome)
for nome, argumentos in (("app", ["--help"]), ("cod", []), ("leads", ["--help"]), ("tratamento", [])):
    sys.argv = [nome] + argumentos
    try:
        runpy.run_module(nome, run_name="__main__")
    except SystemExit as erro:
        assert erro.code == 0
'''
        resultado = subprocess.run([sys.executable, "-B", "-S", "-c", codigo], cwd=ROOT,
                                   capture_output=True, text=True, timeout=15)
        self.assertEqual(0, resultado.returncode, resultado.stderr)

    def test_tela_download_e_recursos_restritos(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "demo"
            shutil.copytree(BASE_DEMO, base)
            with criar_servidor(0, base) as servidor:
                self.assertEqual("127.0.0.1", servidor.server_address[0])
                thread = threading.Thread(target=servidor.serve_forever, daemon=True)
                thread.start()
                url = "http://127.0.0.1:" + str(servidor.server_address[1])
                try:
                    consulta = urlencode({"segmento": "Restaurantes", "cidade": "São Paulo"})
                    with urlopen(url + "/pesquisar?" + consulta, timeout=3) as resposta:
                        tela = resposta.read().decode()
                    self.assertEqual(3, tela.count('data-perfil="sintetico"'))
                    download = re.search(r'href="(/download.csv\?id=[^"]+)"', tela).group(1)
                    pagina = base / "perfis/restaurante-a.html"
                    pagina.write_text(pagina.read_text().replace(">0012<", ">9999<"), encoding="utf-8")
                    with urlopen(url + download, timeout=3) as resposta:
                        self.assertIn("attachment", resposta.headers["Content-Disposition"])
                        self.assertEqual((ROOT / "examples/resultado-sintetico.csv").read_bytes(), resposta.read())
                    with urlopen(url + "/pesquisar?segmento=Oficinas&cidade=Sao%20Paulo", timeout=3) as resposta:
                        vazio = resposta.read().decode()
                    self.assertNotIn('data-perfil="sintetico"', vazio)
                    download_vazio = re.search(r'href="(/download.csv\?id=[^"]+)"', vazio).group(1)
                    with urlopen(url + download_vazio, timeout=3) as resposta:
                        reader = csv.DictReader(io.StringIO(resposta.read().decode()))
                        self.assertEqual(list(COLUNAS), reader.fieldnames)
                        self.assertEqual([], list(reader))
                    for caminho in ("/cod.py", "/.git/config", "/../README.md"):
                        with self.assertRaises(HTTPError) as erro:
                            urlopen(url + caminho, timeout=3)
                        self.assertEqual(404, erro.exception.code)
                    with self.assertRaises(HTTPError) as erro:
                        urlopen(url + "/pesquisar?segmento=Restaurantes", timeout=3)
                    self.assertEqual(400, erro.exception.code)
                finally:
                    servidor.shutdown()
                    thread.join(timeout=3)

    def test_configuracao_externa_isolada_por_leitura(self):
        arvore = ast.parse((ROOT / "externo.py").read_text())
        topo = [no for no in arvore.body if isinstance(no, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any("selenium" in ast.unparse(no) or "requests" in ast.unparse(no) for no in topo))
        coleta = next(no for no in arvore.body if isinstance(no, ast.FunctionDef) and no.name == "coletar")
        self.assertTrue(any(isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                            and no.func.attr == "get" and any(k.arg == "timeout" for k in no.keywords)
                            for no in ast.walk(coleta)))
        self.assertTrue(any(isinstance(no, ast.Try) and any("driver.quit()" in ast.unparse(f) for f in no.finalbody)
                            for no in ast.walk(coleta)))


if __name__ == "__main__":
    unittest.main()
