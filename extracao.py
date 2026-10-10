"""Extração semântica das páginas HTML locais, usando biblioteca padrão."""

from html.parser import HTMLParser

CAMPOS = ("nome", "publicacoes", "seguidores", "bio", "link", "contato")


class PerfilHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.campos = {}
        self.profundidade = 0
        self.capturas = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("meta", "link", "br", "hr", "img", "input"):
            return
        self.profundidade += 1
        campo = attrs.get("data-campo")
        if campo not in CAMPOS or campo in self.campos:
            return
        if campo == "link":
            self.campos[campo] = attrs.get("href", "").strip()
        else:
            self.capturas.append((self.profundidade, campo, []))

    def handle_data(self, texto):
        for _, _, partes in self.capturas:
            partes.append(texto)

    def handle_endtag(self, tag):
        if tag in ("meta", "link", "br", "hr", "img", "input"):
            return
        for captura in self.capturas[:]:
            nivel, campo, partes = captura
            if nivel == self.profundidade:
                self.campos[campo] = "".join(partes).strip()
                self.capturas.remove(captura)
        self.profundidade = max(0, self.profundidade - 1)


def extrair_html(texto):
    parser = PerfilHTML()
    parser.feed(texto)
    parser.close()
    return {campo: parser.campos.get(campo, "") for campo in CAMPOS}


def ler_perfil(candidato):
    return extrair_html(candidato["caminho"].read_text(encoding="utf-8"))
