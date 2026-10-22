# Teste no Mac — checklist rápido (~20 min)

> Tudo local. Nada é publicado. Se algo der errado, anote o que viu e mande o `~/.tamagoshi_cripto/crash.log`.

## 1. Preparar (uma vez)
```bash
# Python 3.9+ (o do sistema serve; se não tiver: brew install python@3.12 python-tk@3.12)
python3 --version
python3 -c "import tkinter; print(tkinter.TkVersion)"      # precisa imprimir 8.6 (ou 9.0)

cd ~/Downloads && unzip -o tamagoshi.zip && cd tamagoshi
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" || pip install -e . pytest
```

## 2. Rodar
```bash
TAMAGOSHI_CONFIG=/tmp/tama_teste.json tamagoshi       # config limpa → mostra o onboarding
# depois, com a config de verdade:
tamagoshi
tamagoshi --tui                                       # modo terminal
```

## 3. O que conferir (marque ✅/❌)
- [ ] **Onboarding**: o ovo balança, trinca e choca; escolher moeda (← →), digitar um nome com acento (ex.: "Ação"), dicas, opt-ins, **PULAR** funciona.
- [ ] **Transparência**: sem retângulo preto/branco em volta do bicho e do balão (fundo `systemTransparent`). Arrastar pela tela.
- [ ] **Fonte pixel**: textos nítidos, sem fonte do sistema; acentos (ã, é, ç) aparecem.
- [ ] **Som**: clique no bicho (bip), `P` → mini-game com sons; menu → Aparência → *Música de fundo* toca e para. Usa `afplay`.
- [ ] **Clique direito / ctrl-clique** abre o menu; **crase** (`` ` ``) abre o console (no teclado ABNT2 a crase é tecla morta: aperte crase + espaço).
- [ ] **Mini-game**: setas ← → respondem sem atraso; termina em 20 s e dá XP.
- [ ] **Chapéu de halloween** aparece (em outubro). Menu → Aparência → desligar *Chapéus de época* tira.
- [ ] **Alto contraste** e **Tamanho 1x…6x** redesenham certo (sem cortar).
- [ ] **Menu bar (experimental)**: `"menubar_mac": true` na config → reabrir → ícone aparece na barra; *Esconder* e *Mostrar* funcionam.
- [ ] **Abrir ao iniciar** (Pro): cria `~/Library/LaunchAgents/com.tamagoshi.cripto.plist`.
- [ ] **CPU**: Monitor de Atividade → processo `Python` parado deve ficar perto de **1–2 %**. Ou:
      `python tools/medir_cpu.py 60` (num Terminal com sessão gráfica).
- [ ] **Share**: console `share` → PNG em `~/Pictures` e o navegador abre o X com o texto (não posta nada).
- [ ] **Relatório**: menu → Ajuda → *Enviar relatório* abre uma issue preenchida no navegador (não envia sozinho).

## 4. Testes automáticos
```bash
python -m pytest -q          # deve passar tudo (o teste de GUI abre e fecha janelas rapidinho)
```

## 5. Build do .app
```bash
./tools/build_mac.sh
open "dist/Tamagoshi Cripto.app"      # 1ª vez: botão direito → Abrir (app sem assinatura)
```
- [ ] O `.app` abre, tem ícone, som e fonte iguais ao `tamagoshi` do terminal.
- [ ] Apple Silicon e Intel: o build gera para a arquitetura da máquina em que rodou.

## 6. Me conta
Tire prints de qualquer coisa estranha (⌘⇧4) e anote: modelo do Mac, versão do macOS, `python3 --version`.
