# Privacidade do Tamagoshi Cripto 🔒

Resumo: **o bicho mora no seu computador.** Nada sai daqui sem você ligar. Sem conta, sem telemetria, sem analytics.

## O que o app faz na rede (e só isso)
| O quê | Pra onde | Manda o quê | Padrão |
|---|---|---|---|
| Preços | api.coingecko.com | lista de moedas | ligado |
| Blocos, fees, baleias | mempool.space | nada seu (só lê) | ligado |
| Saldo watch-only BTC/ETH/SOL | mempool.space / RPCs públicos | **só o endereço público** que você colou | desligado |
| Manchetes | feeds RSS públicos | nada | ligado (desliga em Ajustes > GRANA) |
| Checar versão nova | api.github.com | nada | ligado (Ajustes > SOBRE) |
| Ranking | servidor que **você** configurar | apelido, XP, nível, estágio, blocos, nº de conquistas, id aleatório | **opt-in** |
| IA (BYO) | a URL que **você** configurar | sua pergunta + humor/preço/nível | **opt-in** |
| Twitch | irc.chat.twitch.tv (login anônimo) | nada (só lê o chat) | **opt-in** |
| Relatório de erro | abre o navegador numa issue preenchida | só o que você revisar e enviar | manual, 2 cliques |

## O que nunca acontece
- Nunca pedimos **seed, chave privada, xprv ou keypair** — o app recusa e dá bronca se você colar.
- Nunca enviamos e-mail, nome real ou endereço de carteira pro ranking.
- Nada é instalado sozinho: "update" só abre a página do Release.

## Onde ficam seus dados
- `~/.tamagoshi_cripto.json`: config, progresso, endereços públicos (se você colou).
- **Chave da IA**: no chaveiro do sistema (Keychain / Credential Manager / Secret Service) via `keyring`
  (`pip install tamagoshi-cripto[secure]`). Sem chaveiro, cai pro JSON local (o console avisa onde ficou).
  Chaves antigas no JSON são migradas sozinhas pro chaveiro no próximo start.
- `~/.tamagoshi_api_token` (permissão 0600): token das rotas de escrita da API local.

## API local (127.0.0.1:8737)
- Escuta **só** em 127.0.0.1; recusa `Host` que não seja localhost (anti DNS-rebinding).
- Sem CORS aberto: um site qualquer no seu navegador **não** consegue ler seu status.
- `/status` sai com endereço de carteira mascarado (`bc1qxy…0wlh`) e sem e-mail/licença.
- Escrita (`POST /pet`, `/feed`) desligada por padrão (`"api_escrita": true` liga) e exige `Authorization: Bearer <token>`.

## Apagar tudo
Apague `~/.tamagoshi_cripto.json`, `~/.tamagoshi_api_token` e, se usou, a entrada `tamagoshi-cripto` do chaveiro.

## Saldo das carteiras (v1.6)
O saldo das carteiras watch-only é consultado em APIs públicas (mempool.space, publicnode, Solana RPC) e cotado na CoinGecko. Ele fica **só na memória**: não é salvo em disco, não aparece na API local, no card, no ranking, no overlay nem é enviado pra IA. `saldo off` esconde os valores na tela.
