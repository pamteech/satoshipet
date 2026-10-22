#!/usr/bin/env bash
# Plugin do sketchybar: mostra o bichinho na barra do Mac.
# sketchybarrc:
#   sketchybar --add item tamagoshi right \
#              --set tamagoshi update_freq=30 script="$CONFIG_DIR/plugins/tamagoshi.sh"
# Precisa do app rodando (API local em 127.0.0.1:8737) e do jq.
PORTA="${TAMAGOSHI_API_PORT:-8737}"
S=$(curl -s --max-time 2 "http://127.0.0.1:$PORTA/status") || S=""
if [ -z "$S" ]; then
  sketchybar --set "$NAME" label="🥚 zzz (app fechado)"
  exit 0
fi
LABEL=$(echo "$S" | jq -r '"\(.emoji) \(.moeda) \(.preco_fmt) \(.variacao_pct|tostring|.[0:5])% · LV\(.nivel) · #\(.btc.bloco // "?") · \(.btc.fee_sat_vb // "?") sat/vB"')
case $(echo "$S" | jq -r .humor) in
  moon) COR=0xff38b764 ;; rekt) COR=0xffb13e53 ;; *) COR=0xfff4f4f4 ;;
esac
sketchybar --set "$NAME" label="$LABEL" label.color="$COR"
