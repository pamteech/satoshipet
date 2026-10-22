# Brand skins (sponsored packs) / Skins de marca (pacotes patrocinados)

A **brand pack** is a skin pack paid for by a company. It is a normal shop pack (`src/tamagoshi_cripto/assets/loja/<id>/`
or `~/.tamagoshi_cripto/loja/<id>/`) with `"tipo": "patrocinado"`. Example: `assets/loja/cafe_satoshi/` (a **fictional**
brand, only there to show the format).

## Format

```json
{
  "id": "cafe_satoshi",
  "nome": "Café do Satoshi",
  "tipo": "patrocinado",
  "tier": "free",
  "autor": "Tamagoshi Cripto",
  "creditos": "arte: equipe Tamagoshi",
  "licenca_arte": "MIT",
  "patrocinador": "Café do Satoshi (marca FICTÍCIA de exemplo)",
  "disclosure": "patrocinado",
  "autorizacao": "contract / written authorization id for the trademark",
  "vigencia": {"de": "2026-01-01", "ate": "2026-12-31"},
  "contato": "marcas@exemplo.invalid",
  "preco_sugerido_brl": 0
}
```

Plus `BTC.png` (required) and optional `ETH.png SOL.png DOGE.png PEPE.png`, each a 192x192 sheet
(rows: garimpando, moon, rekt, pulo × 4 frames of 48 px, transparent background). `tools/make_packs.py` shows how to
build recolor packs; hand-drawn sheets are better.

The app **refuses to load** a `patrocinado` pack without `disclosure: "patrocinado"`, `patrocinador`, `autorizacao`
and `vigencia` (see `loja.validar_pack`). Outside `vigencia` the pack disappears from the shop.

## Rules (non-negotiable)

1. **Disclosure, always.** The widget shows a **PATROCINADO** badge while a brand skin is active, the shop shows the
   **PATROCINADO** tag and the sponsor name, and the streamer overlay shows the badge too. No hiding it.
2. **No impersonation.** Only the brand owner (or someone with written authorization) can sponsor a pack with that
   brand. No fake logos, no "official" claims, no lookalike names, no other projects' tokens.
3. **No financial promotion.** No "buy token X", no exchange referral codes inside the art, no price promises,
   no airdrops/giveaways requiring wallets. Crypto brands can appear (logo/colors), shilling can't.
4. **Nothing that tracks users.** A pack is images + JSON. No links that fire on load, no analytics.
5. **Family-friendly pixel art** in the Sweetie-16 palette; the CI skin validator applies.
6. Brand packs are **free for users** (`"tier": "free"`) by default. The brand pays the project, not the user.

## Pricing guidance (suggestion, BRL)

| Package | What the brand gets | Suggested price |
|---|---|---|
| Seasonal skin (1 coin) | 30 days in the shop, PATROCINADO badge | R$ 500 – 1.500 |
| Full pack (5 coins) | 90 days, credit in README/site | R$ 2.000 – 5.000 |
| Launch bundle | full pack + post on the project's social + share card frame | R$ 5.000 – 10.000 |

Price by real reach (downloads, GitHub stars, stream overlay users) and be upfront about the numbers. Put the
agreement in writing (scope, dates, takedown clause, who owns the art). Issue an invoice; in Brazil, check with an
accountant (MEI/Simples) before the first deal.

## Artist collabs (revenue share)

`"tipo": "colab"` packs need `revenue_share` summing to 100 (e.g. `{"artista": 70, "projeto": 30}`) and credits.
They are sold as **codes** (`"tier": "codigo"`) through the usual license provider (Gumroad/Lemon/Hotmart):
`TAMAGOSHI_LICENSE_SECRET=... python tools/keygen.py --pack neon_nights buyer@email.com` → `SKIN-NEON_NIGHTS-...`
(or `'*'` for a promo code for everyone). Pay the artist from the provider's sales report; document it in
`docs/GO_LIVE.md`.

## pt-BR (resumo)

- Pacote de marca = pacote da loja com `"tipo": "patrocinado"` + `disclosure`, `patrocinador`, `autorizacao` e
  `vigencia` obrigatórios (sem isso o app nem carrega).
- Selo **PATROCINADO** sempre visível (widget, loja, overlay). Sem imitar marca alheia, sem shill de token, sem
  rastreamento, grátis pro usuário.
- Preços sugeridos na tabela acima; contrato por escrito; nota fiscal.
