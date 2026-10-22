# Go-live checklist (tudo que a Pamella precisa fazer — nada disso foi feito automaticamente)

Nada foi publicado, deployado ou criado fora deste computador. Ordem sugerida:

## 1. Repositório
- [ ] Criar o repo no GitHub (ex.: `tamagoshi-cripto`), `git remote add origin ...` e `git push -u origin main`.
- [ ] Trocar **`pamteech`** pelo seu usuário em todos os arquivos: `grep -rl pamteech . --exclude-dir=.git | xargs sed -i 's/pamteech/seu-usuario/g'`
      (README badges, `site/config.js`, `site/index.html` meta OG, `share.py`/`config.py` `site`, issue template).

## 2. Licenças Pro — escolha UM provedor
O app lê `licenca_provedor` da config. Pra todo mundo usar o mesmo, mude o **padrão** em
`src/tamagoshi_cripto/config.py` (`PADRAO["licenca_provedor"]` e `PADRAO["licenca_produto"]`/`licenca_url`) antes do build.
Em todos: cache de 24 h + **14 dias de graça offline**; reembolso derruba o Pro na próxima validação online.

| | Gumroad | Lemon Squeezy | Hotmart | Offline (hmac) |
|---|---|---|---|---|
| Bom pra | começar rápido, público gringo | gringo, imposto/VAT resolvido, limite de ativações | público BR, Pix/boleto | MVP/sem loja |
| Precisa de servidor? | não | não | **sim** (`server/licencas.py`) | não |
| Config | `gumroad` + `licenca_produto` = product_id | `lemonsqueezy` + `licenca_produto` = product_id | `servidor` + `licenca_url` | `hmac` |

**Gumroad**
- [ ] Criar o produto (US$ 5–10) → aba *Content* → ligar **"Generate a unique license key per sale"**.
- [ ] Copiar o **product_id** (Edit product → Advanced / ou na resposta da API) → `licenca_produto`.
- [ ] `licenca_provedor = "gumroad"`. URL do produto em `site/config.js` → `gumroad`.

**Lemon Squeezy**
- [ ] Criar loja + produto, em *License keys* ligar a geração e definir o **limite de ativações** (ex.: 3).
- [ ] Copiar o **product_id** → `licenca_produto`; `licenca_provedor = "lemonsqueezy"`. Link de checkout no site.
- [ ] O app usa `/v1/licenses/activate` (1ª vez, guarda `instance_id`) e depois `/validate`. Sem chave de API no app.

**Hotmart** (não tem API pública de license key → webhook)
- [ ] Subir `server/licencas.py` (Docker: `docker build -f server/Dockerfile.licencas -t tamagoshi-licencas server`)
      com HTTPS e env `HOTMART_HOTTOK`, `TAMAGOSHI_LICENSE_SECRET`, `ADMIN_TOKEN` e (opcional) `SMTP_*` pra mandar a chave por e-mail.
- [ ] Hotmart → Ferramentas → **Webhook (API e notificações)**: URL `https://SEU-HOST/hotmart/webhook`, eventos
      *Compra aprovada/completa, reembolsada, chargeback, cancelada*. Copiar o **hottok** → `HOTMART_HOTTOK`.
- [ ] `licenca_provedor = "servidor"`, `licenca_url = "https://SEU-HOST"`.
- [ ] Sem SMTP? Veja as chaves em `curl -H "Authorization: Bearer $ADMIN_TOKEN" https://SEU-HOST/admin/chaves` e mande pela área de membros.

**Offline (hmac)** — o que já existia
- [ ] Segredo forte como GitHub Secret `TAMAGOSHI_LICENSE_SECRET`; chaves com `python tools/keygen.py email`.
- [ ] Lembrete: quem descompilar o app acha o segredo. Use só pra começar.

## 3. Release (downloads)
- [ ] Trocar `REPO = "pamteech/tamagoshi-cripto"` em `src/tamagoshi_cripto/updates.py` e `crashlog.py` (o aviso de versão nova e o "enviar relatório" usam isso; com pamteech o check fica desligado).
- [ ] `git tag v1.4.0 && git push --tags` → Action **Release** gera `TamagoshiCripto.exe` e `TamagoshiCripto-macos.zip`.
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

## 7. v1.4 (tudo opcional, nada foi feito)
- [ ] **Loja / collab com artista**: combinar por escrito o revenue share (o exemplo é 70/30), trocar o `neon_nights` de
      exemplo pela arte real e créditos reais. Vender o código no provedor de sempre e gerar com
      `TAMAGOSHI_LICENSE_SECRET=... python tools/keygen.py --pack <id> comprador@email` (ou `'*'` = promo pra todos).
- [ ] **Pacote de marca**: só com contrato/autorização de uso da marca; preencher `patrocinador`, `autorizacao`,
      `vigencia`; o selo PATROCINADO é obrigatório (o app recusa sem). Preços sugeridos em `docs/BRAND_SKINS.md`.
      O `cafe_satoshi` é uma marca **fictícia** de exemplo: apague antes de vender o primeiro patrocínio.
- [ ] **Extensão do VS Code**: `cd vscode && npx @vscode/vsce package` já funciona. Publicar exige criar um publisher
      no Marketplace + token (`vsce publish`) e trocar `"publisher": "pamteech"` no `vscode/package.json`.
- [ ] **Card de perfil**: trocar `pamteech` em `.github/workflows/profile-card.yml` e testar no seu repo de perfil.
- [ ] **IA (`ask`)**: continua BYO. Se quiser oferecer IA "de fábrica", isso vira custo seu — não está implementado.
- [ ] **Twitch**: nada a configurar (leitura anônima). Avisar no stream que os comandos são só visuais.
