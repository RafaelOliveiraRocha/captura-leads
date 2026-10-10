"""Tratamento textual e exportação compartilhados; importação sem efeitos."""

import argparse
import csv
import io
import re
from pathlib import Path

COLUNAS = ("PERFIL", "NOME", "PUBLICAÇÕES", "SEGUIDORES", "BIO", "LINK", "CONTATO",
           "SEGMENTO", "CIDADE", "BAIRRO", "ESTADO", "FONTE")
MAPA = {"nome": "NOME", "publicacoes": "PUBLICAÇÕES", "seguidores": "SEGUIDORES",
        "bio": "BIO", "link": "LINK", "contato": "CONTATO"}


def extract_all_numbers(bio):
    return re.findall(r"\b\d{4,5}[-.\s]?\d{4}\b", bio or "")


def preparar_resultado(candidato, campos, fonte):
    linha = {coluna: campos.get(campo, "").strip() for campo, coluna in MAPA.items()}
    if not linha["CONTATO"]:
        linha["CONTATO"] = " / ".join(extract_all_numbers(linha["BIO"]))
    linha.update(PERFIL=candidato["perfil"], SEGMENTO=candidato.get("segmento", ""),
                 CIDADE=candidato.get("cidade", ""), BAIRRO=candidato.get("bairro", ""), FONTE=fonte)
    ausentes = [campo for campo, coluna in MAPA.items() if not linha[coluna]]
    linha["ESTADO"] = "Campos ausentes: " + ", ".join(ausentes) + "." if ausentes else "Completo"
    return linha


def deduplicar(linhas):
    vistos, resultado = set(), []
    for linha in linhas:
        chave = linha["PERFIL"].strip().rstrip("/")
        if chave not in vistos:
            vistos.add(chave)
            resultado.append(linha)
    return resultado


def gerar_csv(linhas):
    saida = io.StringIO(newline="")
    writer = csv.DictWriter(saida, fieldnames=COLUNAS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(linhas)
    return saida.getvalue()


def salvar_csv(linhas, caminho):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("x", encoding="utf-8", newline="") as arquivo:
        arquivo.write(gerar_csv(linhas))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Trata um CSV local e grava um novo arquivo.")
    parser.add_argument("--entrada", type=Path)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args(argv)
    if args.entrada is None or args.saida is None:
        parser.print_help()
        return
    if args.entrada.resolve() == args.saida.resolve():
        parser.error("A saída deve ser diferente da entrada.")
    try:
        with args.entrada.open(encoding="utf-8-sig", newline="") as arquivo:
            reader = csv.DictReader(arquivo)
            antigo = {"IG", "NOME", "N° PUBLICAÇÕES", "N° SEGUIDORES", "BIO", "LINK DA BIO"}
            novo = {"PERFIL", "NOME", "PUBLICAÇÕES", "SEGUIDORES", "BIO", "LINK"}
            nomes = set(reader.fieldnames or ())
            if not (antigo <= nomes or novo <= nomes):
                parser.error("O CSV exige perfil, nome, publicações, seguidores, bio e link.")
            linhas = []
            for item in reader:
                candidato = {"perfil": item.get("PERFIL", item.get("IG", "")),
                             "segmento": item.get("SEGMENTO", ""), "cidade": item.get("CIDADE", ""),
                             "bairro": item.get("BAIRRO", "")}
                campos = {"nome": item.get("NOME", ""), "bio": item.get("BIO", ""),
                          "publicacoes": item.get("PUBLICAÇÕES", item.get("N° PUBLICAÇÕES", "")),
                          "seguidores": item.get("SEGUIDORES", item.get("N° SEGUIDORES", "")),
                          "link": item.get("LINK", item.get("LINK DA BIO", "")),
                          "contato": item.get("CONTATO", "")}
                linhas.append(preparar_resultado(candidato, campos, item.get("FONTE", "CSV local")))
        salvar_csv(deduplicar(linhas), args.saida)
        print("CSV tratado gravado em um novo arquivo.")
    except FileExistsError:
        parser.exit(1, "A saída já existe. Escolha um nome novo.\n")
    except (OSError, TypeError, AttributeError, csv.Error):
        parser.exit(1, "Não foi possível ler ou tratar o CSV. Confira os campos e a codificação.\n")


if __name__ == "__main__":
    main()
