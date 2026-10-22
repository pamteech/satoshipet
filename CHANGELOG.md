# Changelog


## [não lançado] v1.6 (em andamento)
- **SALDO no painel**: carteiras watch-only BTC/ETH/SOL viram `SALDO 0.0123 BTC ≈ R$ 7.450` (R$ em pt-BR, US$ no resto; Ajustes > "Saldo em").
- **Esconder saldo** (`saldo off` / Ajustes): mostra `••••`, ideal pra gravar vídeo. Marcos (0.01 BTC, 1 ETH...) ganham comemoração leve.
- Saldo vive só na memória: fora do disco, do status, da API local, do card, ranking, overlay e IA. Cotação BRL/USD a cada ~3 min com backoff.
- Mac: teclado funciona na janela sem borda; sprite aparece na janela transparente; idioma "auto" lê o idioma do macOS.

## 1.5.0 — "Quality" (2026-10-22)

### 🐛 Bugs corrigidos (achados pelo soak de 24h simuladas + fuzz)
1. Código de pet forjado com checksum válido derrubava o `importar` (AttributeError).
2. Sem limite na descompressão do código de pet (zip bomb) — agora teto de 4 KB.
3. Nome de pet aceitava caracteres invisíveis/RTL.
4. Erro de rede aparecia cru no console ("erro: ...") — agora "sem rede agora".
5. Histórico do console sem limite e guardando a chave da IA — limitado a 100 e mascarado.
6. Link da baleia continuava clicável depois que o toast sumia.
7. Batalha podia rodar pra sempre — teto de 60 jogadas, decide no HP.
8. `renascer()` com o bicho vivo zerava o XP.
9. Testes: fakes de rede do test_gui vazavam pros testes seguintes (fixture de restauração).
10. **Privacidade**: a API local mandava `Access-Control-Allow-Origin: *` — qualquer site aberto no navegador
    lia seu `/status` (com endereço de carteira). Agora sem CORS, com checagem de Host e endereço mascarado.
11. Console limitava a entrada a 60 caracteres: era impossível digitar/colar um código de pet `TAMA1-…`.
12. Chapéus de época cobriam os olhos do sapo; poses tortas (SOL rekt, ETH garimpando…) recentralizadas.

### 🧹 Saúde do código
- `ruff` limpo (config no pyproject), `mypy` no núcleo (17 módulos; regras do jogo com `disallow_untyped_defs`).
- `main.py` (1.390 linhas) dividido em mixins: `desenho`, `entrada`, `menus`, `rede`, `vida`, `graficos` (244 linhas sobram).
- Cobertura 78% → 85% (núcleo: 94%; genetica/logic/multichain/hardcore/evolucao/noticias 100%).
- `tests/soak.py`: relógio falso, preços com choques, quedas de rede, batalhas, loja, hardcore e mortes.

### 🎛️ UX
- **Tela única de Ajustes** com abas (GERAL · VISUAL · GRANA · CONTA · SOBRE) — `S` abre. Substitui os diálogos do Tk.
- **Teclado em tudo**: TAB/Shift+TAB foca, ENTER aperta, setas mudam valor, ESC sai, 1-5 trocam aba; Ctrl+V cola no console.
- **Kit de UI** (`ui.py`): uma paleta, um botão, um anel de foco, um painel.
- **i18n pt-BR / EN** com auto-detecção do sistema (Ajustes > Idioma).
- Confirmações viraram "toque duas vezes" (hardcore, relatório de erro) em vez de pop-up.

### 🎨 Arte
- Formas finais únicas: **Arcanjo Ultrasound** (ETH), **Supernova** (SOL), **Doge Astronauta** (DOGE), **Rei Sapo** (PEPE).
- Pacotes da loja com folhas de ovo/bebê/adulto/whale/diamond.
- Genes de forma (olhos, acessório, padrão) valem nas skins da loja; a paleta continua a do artista.

### 🔒 Segurança / privacidade
- Chave da IA BYO no **chaveiro do sistema** (`keyring`, extra `[secure]`), com fallback e migração automática.
- API local: só 127.0.0.1, anti DNS-rebinding, rotas de escrita `POST /pet` `/feed` (opt-in) com token 0600.
- `pip-audit`: sem vulnerabilidades nas dependências de runtime; mínimos subiram (requests 2.32, Pillow 10.3).
- Novo `PRIVACY.md`.

### 📦 Empacotamento
- Instalação verificada em venv limpo; specs PyInstaller mac/win; rascunhos Homebrew/winget/scoop em `packaging/` (não enviados).

## 1.4.0
Genética e batalhas, hardcore + cemitério, paper trading, ETH/SOL watch-only, baleias, RSS, card de perfil,
extensão VS Code, IA BYO, loja de skins e overlay de streamer.
