"""Busca determinística no catálogo fictício, sem consultas externas."""

import json
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

BASE_DEMO = Path(__file__).resolve().parent / "demo"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def buscar_perfis(segmento, cidade, bairro="", base=BASE_DEMO):
    filtros = (segmento.strip(), cidade.strip(), bairro.strip())
    if not all(filtros[:2]):
        raise ValueError("Informe o segmento e a cidade.")
    if any(len(valor) > 120 for valor in filtros):
        raise ValueError("Use até 120 caracteres em cada filtro.")
    base = Path(base).resolve()
    catalogo = json.loads((base / "catalogo.json").read_text(encoding="utf-8"))
    resultados = []
    for item in catalogo:
        campos = ("segmento", "cidade", "bairro", "perfil", "arquivo")
        if any(not isinstance(item.get(campo), str) for campo in campos):
            raise ValueError("O catálogo exige segmento, cidade, bairro, perfil e arquivo textuais.")
        url = urlsplit(item["perfil"])
        if url.scheme != "https" or not (url.hostname or "").endswith(".example.invalid"):
            raise ValueError("Os perfis da demonstração devem usar https e .example.invalid.")
        arquivo = (base / item["arquivo"]).resolve()
        if not arquivo.is_relative_to(base / "perfis") or arquivo.suffix != ".html":
            raise ValueError("Use somente páginas HTML dentro de demo/perfis.")
        if all(not filtro or normalizar(filtro) in normalizar(item[campo])
               for filtro, campo in zip(filtros, ("segmento", "cidade", "bairro"))):
            resultados.append(dict(item, caminho=arquivo))
    return resultados
