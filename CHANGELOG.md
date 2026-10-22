# Changelog


## [não lançado] v1.7 (em andamento)
- **Novo nome: SatoshiPet** (antes "Tamagoshi Cripto"). Pacote Python `satoshipet`, comando `satoshipet` (o `tamagoshi` segue como apelido deprecado), `SatoshiPet.app` / `SatoshiPet.exe`, bundle id `com.pamtech.satoshipet`, repo `pamteech/satoshipet`. **Nada se perde**: na 1ª abertura o app COPIA `~/.tamagoshi_cripto.json`, `~/.tamagoshi_cripto/` e `~/.tamagoshi_api_token` pros nomes novos (`~/.satoshipet*`; o antigo fica de backup), traz a chave da IA do chaveiro antigo e troca o "iniciar com o sistema" antigo pelo novo. Chaves Pro e códigos SKIN- antigos continuam valendo; variáveis `TAMAGOSHI_*` ainda são aceitas.
- **Clima real** (Open-Meteo, sem chave, DESLIGADO por padrão): cidade (geocoding Open-Meteo) ou `lat,lon` em Ajustes > Geral; "auto" por IP (ipwho.is) só se você escolher. Chuva + guarda-chuva, óculos escuros no sol (em cima dos olhos detectados na folha), neve, neblina pontilhada, tempestade com relâmpago, estrelas e lua à noite. Atualiza a cada ~30 min, cache, backoff, offline usa o último clima.
- **Calendário cripto**: Genesis (03/01), Pizza Day (22/05, com fatia de pizza), Whitepaper Day (31/10), Natal, Carnaval (calculado pela Páscoa) e **halving** (próximo pela altura do bloco; contagem nos últimos ~2016 blocos; festa no bloco do halving). Chapéus novos: festa e tiara de plumas.
- **Conquistas de mercado** com medalhas 8x8: Survivor -10% (24h), ATH ao vivo (ATH da CoinGecko a cada 6 h), HODL 30 dias, Acordou com baleia, Bloco do Halving, Medo Extremo.
- **Amigos na LAN** (opt-in): broadcast UDP 47474 com só nome/espécie/skin/humor/emote e um id aleatório por sessão; validação estrita, limite de taxa e de amigos; visita entra pela borda, troca emote e vai embora (no máx. 1 a cada 10 min).
- **Acessibilidade**: Reduzir movimento (segue o macOS "Reduzir movimento" e as animações do Windows), Fonte grande (2x, layout maior), alto contraste, voz opcional (say/SAPI/spd-say, 1 fala a cada 10 s), `M`/Shift+F10 abre o menu pelo teclado, `Tab`/Shift+Tab passeia pelas dicas (e fala).

## [não lançado] v1.6 (em andamento)
- **SALDO no painel**: carteiras watch-only BTC/ETH/SOL viram `SALDO 0.0123 BTC ≈ R$ 7.450` (R$ em pt-BR, US$ no resto; Ajustes > "Saldo em").
- **Esconder saldo** (`saldo off` / Ajustes): mostra `••••`, ideal pra gravar vídeo. Marcos (0.01 BTC, 1 ETH...) ganham comemoração leve.
- Saldo vive só na memória: fora do disco, do status, da API local, do card, ranking, overlay e IA. Cotação BRL/USD a cada ~3 min com backoff.
- **Transições pixel**: dissolve (Bayer 4x4), wipe diagonal e mosaico entre telas (onboarding, ajustes, cenas) e na troca de humor MOON/REKT.
- **Evolução estilo Pokémon**: silhueta piscando forma velha/nova cada vez mais rápido, flash, brilhos em órbita, som e "EVOLUIU!".
- **Idle vivo**: pisca (às vezes duas vezes), boceja e espreguiça quando fica parado/de madrugada, fidget, e a cabeça segue o mouse.
- **Dicas no hover** (pt/EN) em corações, XP, preço, PRO, botão e nas linhas FEE/F&G/HASH/BLOCO/GAS/SALDO/PAPEL.
- **Modo economia** (padrão ligado, Ajustes > Geral): na bateria FPS e rede pela metade; tela travada/ausente 15 min = pausa (CPU ~0) e rede 10x mais lenta; volta sozinho.
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
