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
