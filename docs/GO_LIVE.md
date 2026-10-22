# Go-live checklist (tudo que a Pamella precisa fazer — nada disso foi feito automaticamente)

Nada foi publicado, deployado ou criado fora deste computador. Ordem sugerida:

## 1. Repositório
- [ ] Criar o repo no GitHub (ex.: `tamagoshi-cripto`), `git remote add origin ...` e `git push -u origin main`.
- [ ] Trocar **`OWNER`** pelo seu usuário em todos os arquivos: `grep -rl OWNER . --exclude-dir=.git | xargs sed -i 's/OWNER/seu-usuario/g'`
      (README badges, `site/config.js`, `site/index.html` meta OG, `share.py`/`config.py` `site`, issue template).

## 2. Licenças Pro (Gumroad)
- [ ] Gerar segredo forte e salvar como GitHub Secret `TAMAGOSHI_LICENSE_SECRET`.
- [ ] Criar produto no Gumroad (US$ 5–10). Colar a URL em `site/config.js` → `gumroad`.
- [ ] Gerar chaves com `TAMAGOSHI_LICENSE_SECRET=... python tools/keygen.py email` (ou integrar a API do Gumroad — ver `license.py`).

## 3. Release (downloads)
- [ ] `git tag v1.2.0 && git push --tags` → Action **Release** gera `TamagoshiCripto.exe` e `TamagoshiCripto-macos.zip`.
      Os links do site (`releases/latest/download/...`) passam a funcionar sozinhos.
- [ ] (Opcional) assinar/notarizar no Mac e assinar o .exe para tirar o aviso de "app não assinado".

## 4. Site (GitHub Pages)
- [ ] Settings → Pages → Source: **GitHub Actions**.
- [ ] Actions → **Site (GitHub Pages)** → *Run workflow*. (Para deploy automático, descomente o `push` em `.github/workflows/pages.yml`.)
- [ ] Testar o card OG em https://cards-dev.x.com/validator ou colando o link num post rascunho.
- [ ] (Opcional) domínio próprio: arquivo `site/CNAME` + DNS.

## 5. Ranking (opcional)
- [ ] Subir `server/` em um host de containers com HTTPS (Fly.io, Render, Railway, VPS + Caddy):
      `docker build -t tamagoshi-ranking server && docker run -p 8740:8740 -v data:/data tamagoshi-ranking`
- [ ] Colocar a URL em `site/config.js` → `rankingUrl` e, se quiser, como padrão em `config.py` → `ranking_url`
      (o ranking continua desligado até cada pessoa digitar `rank on <apelido>`).
- [ ] Moderação: apelidos são livres (3–16 chars). Para remover alguém: `sqlite3 ranking.db "DELETE FROM jogadores WHERE nick='x'"`.

## 6. Afiliado e divulgação
- [ ] Trocar `LINK_AFILIADO` em `src/tamagoshi_cripto/config.py` (confira as regras do programa e da sua jurisdição).
- [ ] Abrir a primeira issue "🏆 Concurso de skins" e fixar (pinned). Definir prêmio e prazo.
- [ ] Postar os GIFs de `docs/demo/` e o `docs/share_card.png`.
