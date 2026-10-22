# Contributing 🐣

Thanks for wanting to make the pet even more degen! The easiest (and most fun) way to contribute is **adding a creature**.

## Dev setup

```bash
git clone https://github.com/OWNER/tamagoshi-cripto && cd tamagoshi-cripto
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
tamagoshi            # desktop window
tamagoshi --tui      # terminal mode
pytest               # Linux GUI tests: xvfb-run -a pytest
```

## Add a community creature (no Python needed)

A creature is a folder with two files:

```
my-creature/
├── skin.json
└── sheet.png
```

### `sheet.png`
- **192×192 RGBA**, a grid of **48×48** frames.
- **4 rows** (top to bottom): `garimpando` (sideways market), `moon` (> +2%), `rekt` (< −2%), `pulo` (reaction when clicked).
- **4 columns** = 4 animation frames (played at ~180 ms each, looping).
- Background **fully transparent**, and **only alpha 0 or 255** (no semi-transparency: Windows uses a color key to make the window see-through).
- Keep the feet around y = 44 so it sits on the same "floor" as the built-in pets.
- Tip: use a limited palette ([Sweetie 16](https://lospec.com/palette-list/sweetie-16) is what the built-ins use), a 1-px dark outline, and light coming from the top-left.

### `skin.json`
```json
{
  "id": "slime",
  "nome": "Slime da Liquidez",
  "autor": "your-github-handle",
  "descricao": "A liquidity pool with feelings.",
  "frases": {
    "garimpando": ["providing liquidity..."],
    "moon": ["9000% APY!"],
    "rekt": ["I got drained..."]
  }
}
```
`id`, `nome` and `autor` are required; `frases` (extra speech-bubble lines per mood) is optional.

### Try it
Drop the folder in `~/.tamagoshi_cripto/skins/` (or pass `--skins-dir path/`), then:
```bash
tamagoshi --list-skins
tamagoshi --skin plugin:slime
tamagoshi --tui --skin plugin:slime
```

### Submit it
Put it in `src/tamagoshi_cripto/assets/skins/<id>/` and open a PR. The CI validates the format. See `tools/exemplo_skin.py` for a creature drawn in code with the built-in pixel engine (`tamagoshi_cripto/pixel.py`: shaded volumes, dithering, sel-out outlines, squash & stretch).

**Rules:** original art only (no copyrighted characters or exchange logos), keep it fun, no financial advice.

## Changing built-in sprites
The built-ins are drawn in code in `src/tamagoshi_cripto/sprites.py`. After editing, run:
```bash
python -m tamagoshi_cripto.sprites   # regenerates sheets, docs/sprites_preview.png and docs/demo/*.gif
```
and commit the results. A test checks that committed sheets match the generator.

## Code style
Small modules, comments welcome (pt-BR or English), tests for any logic. The GUI only touches widgets from the Tk main thread; network calls live in background threads.

## Evolution stages (v1.1)
Each creature has one sheet per stage: `COIN_SKIN_ovo.png`, `COIN_SKIN_bebe.png`, `COIN_SKIN.png` (adult),
`COIN_SKIN_whale.png`, `COIN_SKIN_diamond.png` — same 192×192 / 4×4 layout. Run `python -m tamagoshi_cripto.sprites`
to regenerate all 125 (~16 s). Plugin skins currently use their single sheet for every stage; a missing built-in stage sheet falls back to the adult one.

## Adding a console command
Add a `cmd_<name>(self, args)` method to `console.Console` returning a list of lines (pt-BR, fun tone),
add it to `AJUDA`, and add a case to `tests/test_nerd.py` (use the fake `Ctx`, never the network).
It works in the window and in `--tui` automatically.

## Rules for on-chain features
- Keyless, free, public APIs only, with timeouts. Never block the Tk thread; push events to the queue.
- Offline must degrade to `?`, never a crash.
- **Never** add anything that asks for private keys, seeds or signing. Watch-only forever.

## Concurso de skins / Skin contest 🏆
**PT:** abra uma issue com o template **🏆 Concurso de skins** e mande o PR com a pasta
`src/tamagoshi_cripto/assets/skins/<id>/` (`sheet.png` + `skin.json`, formato acima).

Regras (checadas por `tools/validate_skin.py` e pela Action **Skin contest check** em todo PR que mexe em skins):
- `id` em `[a-z0-9_-]`, igual ao nome da pasta; `nome` e `autor` obrigatórios
- `sheet.png` 192×192, 4 linhas (garimpando, moon, rekt, pulo) × 4 frames de 48×48
- fundo 100% transparente, alfa só 0 ou 255, no máximo **32 cores**, nenhum frame vazio
- frases opcionais com até 60 caracteres
- arte **original** (sem personagem/logo de terceiros), licenciada MIT junto com o projeto

```bash
python tools/validate_skin.py src/tamagoshi_cripto/assets/skins/minha_skin --preview previews/
# abre previews/minha_skin.png (4x) e previews/minha_skin.gif
```
A Action anexa o preview como artifact **skin-preview** e escreve um resumo no PR.
Julgamento sugerido: votos com 👍 na issue + escolha da mantenedora. Prêmio sugerido: licença Pro + skin no app.

**EN:** open an issue with the **🏆 Concurso de skins** template and a PR adding your folder under
`src/tamagoshi_cripto/assets/skins/<id>/`. Run `python tools/validate_skin.py <folder> --preview previews/`
locally; CI runs the same checks and uploads a `skin-preview` artifact.

## Site, share card, leaderboard
- `site/` is plain HTML/CSS/JS. Preview with `cd site && python -m http.server 8765`.
  Regenerate assets with `PYTHONPATH=src python tools/site_assets.py` and screenshots with
  `python tools/site_screenshots.py` (needs Chrome).
- `share.py` draws the 1200×675 card on a 400×225 grid scaled 3× — keep it pixel-perfect (no smoothing).
- `server/ranking.py` is stdlib-only on purpose. Any new field must be non-personal and added to the whitelist + tests.

## v1.3 internals
- **Scenes** (`cenas.py`): onboarding and the mini-game take over the canvas via `app.cena` (`desenhar/tecla/clique/tick`).
  The mini-game has its own 50 ms loop that only runs while it's open — keep the idle path at the 180 ms animation tick.
- **Sounds** (`sons.py`): add a jingle to `MUSICAS` using note names (`"C5 E5 G5:2"`), channels `p1`/`p2`/`ruido`.
- **Hats** (`juice.py`): ASCII pixel art drawn on the 48×48 frame before scaling. Check renders of all 5 coins × moods.
- **Licensing** (`licencas.py`): a provider is a function `(cfg, email, key, http) -> Resultado`; raise `SemRede` for
  network errors (triggers the grace period). Messages in pt-BR. Tests mock HTTP (`tests/test_v13.py`).
- **Config**: bump `VERSAO_CONFIG` and add a step to `config.migrar()` when you rename/restructure keys.
- **Performance**: run `xvfb-run -a python tools/medir_cpu.py 60` before/after anything that touches the draw loop.

## v1.4 internals
- **Mixins**: `engajamento.py` (DNA, breeding, battles, hardcore), `mercado.py` (paper trading, ETH/SOL, whales, RSS),
  `lojinha.py` (shop, stream overlay, Twitch) are mixed into `Tamagoshi`. Network work stays in threads that only push
  to `app.eventos`; `_evento_mercado` handles them on the Tk thread.
- **DNA** (`genetica.py`): genes are recolors/overlays applied to the 48×48 frame **before** scaling, only with
  Sweetie-16 colors (a test checks every coin × 25 seeds). New gene option = add it to `GENES` (weight, rarity points)
  and to the tables; keep `importar()` strict (friend codes are untrusted input).
- **Battles** (`batalha.py`): pure and deterministic given a seed. Balance changes need `tests/test_v14_engajamento.py`.
- **Keys and seeds**: any new chain goes through a `validar()` that refuses private keys/seeds *before* anything is
  stored or sent (see `multichain.py` and its parametrized tests).
- **Keyless only**: new data sources must work without an API key. Anything needing a key is BYO and off by default
  (`ai.py` is the model).
- **Shop packs** (`loja.py`): folder + `pack.json` + 192×192 sheets. `patrocinado` packs require disclosure,
  sponsor, authorization and dates — see [docs/BRAND_SKINS.md](docs/BRAND_SKINS.md). Generate examples with
  `python tools/make_packs.py`.
- **VS Code** (`vscode/`): plain JS, zero deps. `node vscode/test/smoke.js`, `cd vscode && npx @vscode/vsce package`.
