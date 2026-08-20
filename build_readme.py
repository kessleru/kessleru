#!/usr/bin/env python3
"""
Gera dark_mode.svg e light_mode.svg para o README do perfil do GitHub.

- A arte ASCII vem de ascii_art.txt
- As informacoes vem de perfil.json
- As estatisticas vem da API do GitHub (se ACCESS_TOKEN estiver definido)

Uso local:
    export ACCESS_TOKEN=ghp_xxx        # token classico com escopo read:user, repo
    export USER_NAME=kessleru
    python build_readme.py
"""

import json
import os
import datetime as dt
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
TOKEN = os.environ.get("ACCESS_TOKEN", "")
USER = os.environ.get("USER_NAME") or json.loads(
    (RAIZ / "perfil.json").read_text(encoding="utf-8")
)["usuario_github"]

API = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"bearer {TOKEN}"}

# ---------------------------------------------------------------- tema

TEMAS = {
    "dark_mode.svg": {
        "fundo": "#161b22",
        "texto": "#c9d1d9",
        "chave": "#ffa657",
        "valor": "#a5d6ff",
        "pontos": "#616e7f",
        "borda": "#30363d",
    },
    "light_mode.svg": {
        "fundo": "#ffffff",
        "texto": "#24292f",
        "chave": "#953800",
        "valor": "#0550ae",
        "pontos": "#8c959f",
        "borda": "#d0d7de",
    },
}

LARGURA_CHAR = 9.7   # largura efetiva de um caractere (Consolas 16px com size-adjust)
ALTURA_LINHA = 20


# ---------------------------------------------------------------- GitHub


def graphql(query, variaveis):
    r = requests.post(API, json={"query": query, "variables": variaveis},
                      headers=HEADERS, timeout=30)
    r.raise_for_status()
    dados = r.json()
    if "errors" in dados:
        raise RuntimeError(dados["errors"])
    return dados["data"]


def buscar_stats():
    """Retorna o dicionario de estatisticas. Sem token, devolve o cache."""
    cache = RAIZ / "stats_cache.json"
    if not TOKEN:
        print("ACCESS_TOKEN ausente - usando stats_cache.json")
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        return {
            "uptime": "-", "repos": "-", "contrib": "-", "stars": "-",
            "commits": "-", "followers": "-", "top_lang": "-",
        }

    perfil = graphql(
        """
        query($login: String!) {
          user(login: $login) {
            createdAt
            followers { totalCount }
            repositories(ownerAffiliations: OWNER, first: 1) { totalCount }
            repositoriesContributedTo(
              first: 1,
              contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]
            ) { totalCount }
          }
        }
        """,
        {"login": USER},
    )["user"]

    criado = dt.datetime.fromisoformat(perfil["createdAt"].replace("Z", "+00:00"))

    # commits de todos os anos desde a criacao da conta
    commits = 0
    ano = criado.year
    hoje = dt.datetime.now(dt.timezone.utc)
    while ano <= hoje.year:
        ini = max(criado, dt.datetime(ano, 1, 1, tzinfo=dt.timezone.utc))
        fim = min(hoje, dt.datetime(ano, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        d = graphql(
            """
            query($login: String!, $de: DateTime!, $ate: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $de, to: $ate) {
                  totalCommitContributions
                  restrictedContributionsCount
                }
              }
            }
            """,
            {"login": USER, "de": ini.isoformat(), "ate": fim.isoformat()},
        )["user"]["contributionsCollection"]
        commits += d["totalCommitContributions"] + d["restrictedContributionsCount"]
        ano += 1

    # estrelas e linguagens, paginando os repositorios
    stars, linguagens, cursor = 0, {}, None
    while True:
        d = graphql(
            """
            query($login: String!, $cursor: String) {
              user(login: $login) {
                repositories(ownerAffiliations: OWNER, isFork: false,
                             first: 100, after: $cursor) {
                  pageInfo { hasNextPage endCursor }
                  nodes {
                    stargazerCount
                    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                      edges { size node { name } }
                    }
                  }
                }
              }
            }
            """,
            {"login": USER, "cursor": cursor},
        )["user"]["repositories"]
        for repo in d["nodes"]:
            stars += repo["stargazerCount"]
            for e in repo["languages"]["edges"]:
                linguagens[e["node"]["name"]] = linguagens.get(e["node"]["name"], 0) + e["size"]
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]

    top = max(linguagens, key=linguagens.get) if linguagens else "-"
    total = sum(linguagens.values()) or 1
    top_lang = f"{top} ({linguagens.get(top, 0) * 100 // total}%)"

    stats = {
        "uptime": formatar_idade(criado, hoje),
        "repos": f"{perfil['repositories']['totalCount']:,}".replace(",", "."),
        "contrib": f"{perfil['repositoriesContributedTo']['totalCount']:,}".replace(",", "."),
        "stars": f"{stars:,}".replace(",", "."),
        "commits": f"{commits:,}".replace(",", "."),
        "followers": f"{perfil['followers']['totalCount']:,}".replace(",", "."),
        "top_lang": top_lang,
    }
    cache.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def formatar_idade(inicio, agora):
    anos = agora.year - inicio.year
    meses = agora.month - inicio.month
    dias = agora.day - inicio.day
    if dias < 0:
        meses -= 1
        anterior = (agora.replace(day=1) - dt.timedelta(days=1)).day
        dias += anterior
    if meses < 0:
        anos -= 1
        meses += 12
    partes = []
    if anos:
        partes.append(f"{anos} ano" + ("s" if anos != 1 else ""))
    if meses:
        partes.append(f"{meses} " + ("meses" if meses != 1 else "mes"))
    partes.append(f"{dias} dia" + ("s" if dias != 1 else ""))
    return ", ".join(partes)


# ---------------------------------------------------------------- render


ESPACO = "\u00a0"   # espaco rigido: nenhum parser colapsa


def esc(txt):
    return (txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace(" ", ESPACO))


def montar_linhas(cfg, stats):
    """Devolve uma lista de (tipo, conteudo) pronta para virar tspans."""
    largura = cfg["largura_coluna"]
    saida = [("titulo", cfg["titulo"])]
    for i, secao in enumerate(cfg["secoes"]):
        if i:
            saida.append(("vazio", ""))
        saida.append(("secao", secao["titulo"]))
        for linha in secao["linhas"]:
            chave = linha["chave"]
            valor = linha["valor"].format(**stats)
            usados = 2 + len(chave) + 1 + 1 + len(valor) + 1  # ". " chave ":" " " ... " " valor
            pontos = max(1, largura - usados)
            saida.append(("dado", (chave, "." * pontos, valor)))
    return saida


def render(cfg, ascii_art, stats, arquivo, tema):
    linhas_info = montar_linhas(cfg, stats)

    col_ascii = max(len(l) for l in ascii_art)
    x_info = int(15 + col_ascii * LARGURA_CHAR + 25)
    largura_info = cfg["largura_coluna"] + 4
    largura_total = int(x_info + largura_info * LARGURA_CHAR + 15)
    altura_total = max(len(ascii_art), len(linhas_info)) * ALTURA_LINHA + 40

    partes = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'font-family="ConsolasFallback,Consolas,Menlo,DejaVu Sans Mono,monospace" '
        f'width="{largura_total}px" height="{altura_total}px" font-size="16px">',
        "<style>",
        "@font-face { src: local('Consolas'), local('Consolas Bold');"
        " font-family: 'ConsolasFallback'; font-display: swap; size-adjust: 109%; }",
        f".chave {{ fill: {tema['chave']}; }}",
        f".valor {{ fill: {tema['valor']}; }}",
        f".pontos {{ fill: {tema['pontos']}; }}",
        f".linha {{ fill: {tema['pontos']}; }}",
        "text, tspan { white-space: pre; }",
        "</style>",
        f'<rect width="{largura_total}px" height="{altura_total}px" '
        f'fill="{tema["fundo"]}" stroke="{tema["borda"]}" rx="15"/>',
        f'<text x="15" y="30" xml:space="preserve" fill="{tema["texto"]}">',
    ]

    for i, linha in enumerate(ascii_art):
        partes.append(f'<tspan x="15" y="{30 + i * ALTURA_LINHA}">{esc(linha)}</tspan>')
    partes.append("</text>")

    partes.append(f'<text x="{x_info}" y="30" xml:space="preserve" '
                  f'fill="{tema["texto"]}">')
    y = 30
    for tipo, conteudo in linhas_info:
        if tipo == "vazio":
            y += ALTURA_LINHA
            continue
        if tipo == "titulo":
            resto = "-" * max(1, cfg["largura_coluna"] - 1 - len(conteudo))
            partes.append(
                f'<tspan x="{x_info}" y="{y}">{esc(conteudo)}{ESPACO}'
                f'<tspan class="linha">{esc(resto)}</tspan></tspan>'
            )
        elif tipo == "secao":
            resto = "-" * max(1, cfg["largura_coluna"] - 3 - len(conteudo))
            partes.append(
                f'<tspan x="{x_info}" y="{y}"><tspan class="linha">-{ESPACO}</tspan>'
                f'{esc(conteudo)}{ESPACO}<tspan class="linha">{esc(resto)}</tspan></tspan>'
            )
        else:
            chave, pontos, valor = conteudo
            partes.append(
                f'<tspan x="{x_info}" y="{y}"><tspan class="pontos">.{ESPACO}</tspan>'
                f'<tspan class="chave">{esc(chave)}</tspan>:'
                f'<tspan class="pontos">{ESPACO}{esc(pontos)}{ESPACO}</tspan>'
                f'<tspan class="valor">{esc(valor)}</tspan></tspan>'
            )
        y += ALTURA_LINHA
    partes.append("</text>")
    partes.append("</svg>")

    (RAIZ / arquivo).write_text("\n".join(partes), encoding="utf-8")
    print(f"gerado {arquivo}  ({largura_total}x{altura_total})")


def main():
    cfg = json.loads((RAIZ / "perfil.json").read_text(encoding="utf-8"))
    ascii_art = (RAIZ / "ascii_art.txt").read_text(encoding="utf-8").split("\n")
    while ascii_art and not ascii_art[-1].strip():
        ascii_art.pop()
    stats = buscar_stats()
    for arquivo, tema in TEMAS.items():
        render(cfg, ascii_art, stats, arquivo, tema)


if __name__ == "__main__":
    main()
