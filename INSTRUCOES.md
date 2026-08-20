# Perfil do GitHub em ASCII

Como o do `Andrew6rant`: o README é uma imagem SVG gerada por script, com a arte
ASCII do lado esquerdo e as informações do lado direito. As estatísticas se
atualizam sozinhas todo dia via GitHub Actions.

## 1. Criar o repositório de perfil

O repositório precisa ter **exatamente o mesmo nome do seu usuário**:

```
github.com/kessleru/kessleru
```

Crie ele público e marque "Add a README file". O GitHub vai mostrar esse README
no topo do seu perfil.

## 2. Subir os arquivos

Copie tudo desta pasta para o repositório:

```
README.md                      aponta para os SVGs
dark_mode.svg                  gerado
light_mode.svg                 gerado
perfil.json                    <- suas informações (edite aqui)
ascii_art.txt                  <- a arte ASCII
build_readme.py                gera os SVGs e busca as stats
gerar_ascii.py                 refaz a arte a partir de outra foto
requirements.txt
stats_cache.json               último resultado das stats
.github/workflows/build.yaml   atualização diária
```

```bash
git clone https://github.com/kessleru/kessleru.git
cd kessleru
# cole os arquivos aqui
git add -A && git commit -m "perfil em ascii" && git push
```

## 3. Criar o token de acesso

As estatísticas precisam de um token para ler commits de repositórios privados.

1. GitHub → Settings → Developer settings → **Personal access tokens (classic)**
2. Generate new token (classic), escopos: `repo` e `read:user`
3. Copie o token

No repositório `kessleru/kessleru` → Settings → Secrets and variables → Actions →
New repository secret, crie os dois:

| Nome | Valor |
|---|---|
| `ACCESS_TOKEN` | o token que você acabou de gerar |
| `USER_NAME` | `kessleru` |

Depois vá na aba **Actions**, escolha "Atualizar README" e clique em
**Run workflow** para rodar a primeira vez.

## 4. Editar suas informações

Tudo que aparece do lado direito está em `perfil.json`. Cada linha é um par
`chave` / `valor`, e os pontinhos são calculados sozinhos:

```json
{ "chave": "OS", "valor": "Windows 11, WSL2" }
```

Valores entre chaves são preenchidos automaticamente pelo script:
`{uptime}`, `{repos}`, `{contrib}`, `{stars}`, `{commits}`, `{followers}`,
`{top_lang}`.

`largura_coluna` controla o comprimento da linha de pontinhos. Se você colocar um
valor muito longo, aumente esse número.

Para testar local antes de subir:

```bash
pip install -r requirements.txt
python build_readme.py           # sem token, usa o cache
```

## 5. Trocar a foto

```bash
pip install pillow numpy
python gerar_ascii.py outra_foto.jpg
```

Ajuste `RECORTE` no topo do `gerar_ascii.py` para enquadrar o rosto (a máscara
espera cabeça no centro e ombros embaixo). `LARGURA` muda a resolução da arte —
entre 40 e 50 colunas fica bom; acima disso o SVG começa a ficar largo demais
para o celular.

## Detalhes

- O `<picture>` no README troca entre `dark_mode.svg` e `light_mode.svg`
  conforme o tema do GitHub do visitante.
- O SVG usa Consolas com `size-adjust: 109%`, o mesmo truque do Andrew6rant,
  para o alinhamento não quebrar em quem não tem a fonte instalada.
- Todos os espaços do SVG são `\u00a0` (espaço rígido), e os `<text>` levam
  `xml:space="preserve"`. Sem isso, alguns renderizadores colapsam os espaços
  do início de cada linha, a arte encosta na margem esquerda e o rosto entorta.
  Se for editar o `build_readme.py`, não troque isso por espaço comum.
- `Uptime` conta desde a criação da sua conta no GitHub.
- O workflow commita sozinho nos SVGs todo dia; se você editar o `perfil.json`,
  o push já dispara uma nova geração.
