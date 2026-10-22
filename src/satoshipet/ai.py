"""ai.py - `ask <pergunta>` no console. BYO (traga sua própria) chave/URL OpenAI-compatível. DESLIGADO por padrão.

Sem ai_url configurada, o bicho responde com sabedoria enlatada (de graça e offline).
Com ai_url (OpenAI, OpenRouter, Groq, Ollama local, LM Studio...), manda SÓ a pergunta + humor/preço/nível.
Nunca manda carteira, e-mail, licença ou histórico. A chave fica no seu config (ou em $SATOSHIPET_AI_KEY).
"""
import random

import requests

ENLATADAS = [
    "olha, eu sou um bicho de pixel. minha única estratégia é HODL e carinho.",
    "não é conselho financeiro, mas... já pensou em fazer carinho em mim?",
    "a resposta é: depende. (a resposta em cripto é sempre 'depende')",
    "perguntei pro Satoshi. ele não respondeu desde 2011.",
    "minha bola de cristal tá em manutenção. tenta 'price' que pelo menos isso eu sei.",
    "few understand. eu também não.",
    "se subir, eu avisei. se cair, eu nunca disse nada.",
    "bom demais pra ser verdade? então é golpe. de nada.",
    "quer IA de verdade? configure: ai set <url> <chave> (é BYO, você que paga)",
]
SISTEMA = ("Você é um SatoshiPet de pixel art que vive no desktop e sente o mercado cripto. Responda em "
           "português do Brasil, em no máximo 2 frases curtas, com humor e gírias cripto. Nunca dê conselho "
           "financeiro: se pedirem, faça piada e diga que não é conselho financeiro. Nunca peça chave privada ou seed.")


def ligado(cfg):
    return bool((cfg.get("ai_url") or "").strip())


def enlatada(pergunta, rnd=random):
    p = pergunta.lower()
    if any(k in p for k in ("seed", "chave privada", "private key", "senha")):
        return "NUNCA compartilhe seed/chave privada. nem comigo. principalmente comigo."
    if any(k in p for k in ("comprar", "vender", "buy", "sell", "vale a pena")):
        return "não é conselho financeiro: compra na fantasia com 'paper buy BTC 100' e vê no que dá."
    return rnd.choice(ENLATADAS)


def perguntar(pergunta, cfg, contexto=None, timeout=25):
    """Retorna a resposta (str). Sem config -> enlatada. Erros de rede -> mensagem amigável."""
    pergunta = (pergunta or "").strip()[:500]
    if not pergunta:
        return "pergunta o quê, anon? ex.: ask o que é halving"
    if not ligado(cfg):
        return enlatada(pergunta)
    url = cfg["ai_url"].rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    from . import segredos
    chave = segredos.ler(cfg)
    ctx = contexto or {}
    msgs = [{"role": "system", "content": SISTEMA + f" Seu estado agora: moeda {ctx.get('moeda')}, humor "
                                                    f"{ctx.get('humor')}, variação {ctx.get('variacao_pct')}%, "
                                                    f"nível {ctx.get('nivel')}."},
            {"role": "user", "content": pergunta}]
    try:
        r = requests.post(url, json={"model": cfg.get("ai_modelo") or "gpt-4o-mini", "messages": msgs,
                                     "max_tokens": 120, "temperature": 0.9},
                          headers={"Authorization": f"Bearer {chave}"} if chave else {}, timeout=timeout)
        if r.status_code == 401:
            return "a IA disse 401: chave errada ou vencida (ai set <url> <chave>)"
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"].strip()
        return txt[:400] or enlatada(pergunta)
    except Exception as e:
        return f"a IA tá fora do ar ({type(e).__name__}). resposta enlatada: {enlatada(pergunta)}"
