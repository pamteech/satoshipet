// SatoshiPet — landing. Sem framework, sem tracker, sem cookie. Só o bicho.
(() => {
  const C = Object.assign({}, window.SATOSHIPET || {});
  const qs = new URLSearchParams(location.search);
  if (qs.get("ranking")) C.rankingUrl = qs.get("ranking");   // teste local: ?ranking=http://127.0.0.1:8740
  if (qs.get("lang")) localStorage.setItem("lang", qs.get("lang"));
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const LINHA = { garimpando: 0, moon: 1, rekt: 2, pulo: 3 };
  const IDS = { BTC: "bitcoin", ETH: "ethereum", SOL: "solana", DOGE: "dogecoin", PEPE: "pepe" };
  const NOMES = { BTC: "Satoshinho", ETH: "Vitalikinho", SOL: "Solzinho", DOGE: "Doguinho", PEPE: "Sapo Degen" };

  // ---------- i18n ----------
  const EN = {
    nav_demo: "demo", nav_feat: "features", nav_price: "pricing", nav_rank: "leaderboard",
    tag: "v1.4 · open source · MIT", h1: "A tiny pet that feels the market <em>harder than you</em>.",
    sub: "Pixel art that floats on your desktop, eats every new Bitcoin block, gets hungry when fees spike and evolves from egg to <b>Whale</b>. It even has a hacker console.",
    dl_mac: "Download for macOS", dl_win: "Download for Windows", dl_src: "pipx / source",
    free_note: "Free forever. Pro is a one-time payment.", m_live: "live",
    demo_note: "Live price (CoinGecko) and block (mempool.space), straight from your browser. Click the pet.",
    g1: "eats real blocks", g2: "evolves into a Whale", g3: "hacker console (`)", crew: "Meet the crew", evo: "Evolution", ou: "or",
    evo_note: "XP from blocks eaten, HODL time and crashes survived. 3 crashes = Diamond Hands.",
    f1: "Satoshinho (BTC), animations, petting, life, 8-bit sounds", f2: "Eats blocks, hunger = fee rate, sleep, hash rate",
    f3: "Evolution egg → Whale / Diamond Hands, XP and level", f4: "Hacker console, hjkl, sats mode, nerd achievements",
    f5: "Watch-only wallet (public address only)", f6: "Local API for sketchybar, polybar, OBS · share card · opt-in leaderboard",
    f7: "Terminal mode (all coins) and community creatures", f8: "ETH, SOL, DOGE and PEPE in the desktop window",
    f9: "Premium skins (cyberpunk, cat, frog)", f10: "Price alerts, thresholds, sparkline, start at login",
    buy: "Buy Pro", buy_note: "One-time payment via Gumroad. The key arrives by e-mail; paste it in “Activate Pro”.",
    rank_t: "Pet leaderboard", rank_note: "Opt-in: in the app, type <code>rank on your_nick</code> in the console. Only a nickname + pet stats.",
    nick: "nick", stage: "stage", blocks: "blocks",
    q1: "Does it ask for my private key or seed?", a1: "<b>Never.</b> The wallet is watch-only: you paste a public address (bc1…, 1…, 3…). If you paste something that looks like a private key, xprv or seed, the app refuses and does not store it. Nobody legit asks for your seed — not even us.",
    q2: "Does it touch my money or trade?", a2: "No. It only reads prices (CoinGecko), blocks and fees (mempool.space). No exchange connection, no signing.",
    q3: "What data leaves my computer?", a3: "Only public price/block queries. The leaderboard is optional and off by default; if you turn it on it sends nickname, XP, level, stage, blocks and achievement count with a random ID. No e-mail, no wallet.",
    q4: "Does it work offline?", a4: "Yes: without internet it shows “?” and stays alive (a bit needy).",
    q5: "macOS/Windows say the app is unsigned", a5: "Mac: right click → Open the first time. Windows: “More info” → “Run anyway”. Or install from source with <code>pipx</code>.",
    q6: "Is this financial advice?", a6: "It's a pixel pet. It cries when the price dips. Not financial advice.",
    n14_t: "New in v1.4", n14_1: "turn-based battles · vs AI or a friend's code", n14_2: "DNA & breeding · rarity and mutations",
    n14_3: "hardcore mode · the Graveyard of Honor",
    n14_4: "Paper trading with fake money · ETH/SOL watch-only wallets · whale alerts · RSS headlines · animated GitHub profile card · VS Code extension · skin shop · OBS overlay with Twitch chat. No API keys.",
    novo_t: "New in v1.3", n1: "the egg hatches on first run · you name your pet", n2: "mini-game: catch the sats (P) → XP",
    n3: "particles, halloween/christmas hats, day/night palette",
    n4: "New chiptune sound design (optional background music) · high contrast and 6 sizes · new-version notice (never auto-installs) · ~1% CPU idle.",
    f11: "Onboarding, mini-game, seasonal hats, chiptune soundtrack, high contrast",
    q7: "Does it auto-update?", a7: "No. It only asks GitHub whether a new version is out and shows a notice with the link. Downloading and installing is always up to you (you can turn the notice off in the menu).",
    foot: "made with sats and coffee ☕", disc: "Not affiliated with Bitcoin, Ethereum, Solana, Dogecoin or PEPE. Prices: CoinGecko. Blocks: mempool.space.",
  };
  const PT = {};
  $$("[data-i18n]").forEach(el => PT[el.dataset.i18n] = el.innerHTML);
  let lang = localStorage.getItem("lang") || ((navigator.language || "pt").startsWith("pt") ? "pt" : "en");
  const FRASES = {
    pt: { moon: ["TO THE MOON!", "wagmi ser", "comprei no topo e tô feliz"], garimpando: ["garimpando...", "HODL", "few understand"],
          rekt: ["REKT. me abraça", "é só uma correção (né?)", "buy the dip... de novo"], carinho: ["hehe", "+2 XP!", "♥ ♥ ♥"],
          bloco: n => `bloco #${n} comido! nhac`, off: "sem internet. tô vivo, só carente." },
    en: { moon: ["TO THE MOON!", "wagmi ser", "bought the top, still happy"], garimpando: ["mining...", "HODL", "few understand"],
          rekt: ["REKT. hug me", "just a correction (right?)", "buy the dip... again"], carinho: ["hehe", "+2 XP!", "♥ ♥ ♥"],
          bloco: n => `block #${n} eaten! nom`, off: "offline. still alive, just needy." },
  };
  function aplicarLang() {
    const d = lang === "en" ? EN : PT;
    $$("[data-i18n]").forEach(el => { if (d[el.dataset.i18n]) el.innerHTML = d[el.dataset.i18n]; });
    document.documentElement.lang = lang === "en" ? "en" : "pt-BR";
    $("#lang").textContent = lang === "en" ? "PT" : "EN";
    falar();
    rankRender();
  }
  $("#lang").onclick = () => { lang = lang === "en" ? "pt" : "en"; localStorage.setItem("lang", lang); aplicarLang(); };

  // ---------- links ----------
  const links = { mac: C.downloadMac || C.releases, win: C.downloadWin || C.releases, repo: C.repo };
  $$("[data-dl]").forEach(a => { a.href = links[a.dataset.dl] || "#"; a.rel = "noopener"; });
  $("#comprar").href = C.gumroad || "#";
  if (C.precoPro) $("#preco-pro").textContent = C.precoPro;

  // ---------- sprites ----------
  const cache = {};
  function folha(nome) {
    if (!cache[nome]) { const i = new Image(); i.src = `assets/sprites/${nome}.png`; cache[nome] = i; }
    return cache[nome];
  }
  function pintar(cv, img, linha, frame) {
    const c = cv.getContext("2d"); c.imageSmoothingEnabled = false;
    c.clearRect(0, 0, 48, 48);
    if (img.complete && img.naturalWidth) c.drawImage(img, frame * 48, linha * 48, 48, 48, 0, 0, 48, 48);
  }
  const est = { moeda: "BTC", humor: "garimpando", forcado: null, var: 0, preco: null, pulo: 0, frase: "", bloco: null, frase_t: 0 };
  const humor = () => est.pulo > 0 ? "pulo" : (est.forcado || est.humor);
  let f = 0;
  setInterval(() => {
    f = (f + 1) % 4;
    pintar($("#pet"), folha(`${est.moeda}_padrao`), LINHA[humor()], f);
    $$(".mini-pet").forEach((cv, i) => pintar(cv, folha(cv.dataset.sheet), [0, 1, 0, 3][(Math.floor(Date.now() / 2400) + i) % 4], (f + i) % 4));
    if (est.pulo > 0) est.pulo--;
  }, 180);

  function falar(txt) {
    const fr = FRASES[lang];
    est.frase = txt || fr[est.forcado || est.humor][Math.floor(Math.random() * 3)];
    $("#balao").textContent = `${NOMES[est.moeda]}: ${est.frase}`;
  }
  $("#pet").onclick = () => { est.pulo = 8; falar(FRASES[lang].carinho[Math.floor(Math.random() * 3)]); };

  // ---------- mercado ao vivo ----------
  const fmt = p => p == null ? "$—" : p >= 1 ? "$" + p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                             : "$" + p.toPrecision(3);
  function painel() {
    $("#p-moeda").textContent = `${est.moeda} · ${NOMES[est.moeda]}`;
    $("#p-preco").textContent = fmt(est.preco);
    const v = $("#p-var"); v.textContent = (est.var >= 0 ? "+" : "") + est.var.toFixed(2) + "%";
    v.className = est.humor === "moon" ? "lima" : est.humor === "rekt" ? "vinho" : "amarelo";
  }
  const precos = {};
  async function mercado() {
    try {
      const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=" + Object.values(IDS).join(",") +
                            "&vs_currencies=usd&include_24hr_change=true", { cache: "no-store" });
      const d = await r.json();
      for (const [s, id] of Object.entries(IDS)) if (d[id]) precos[s] = { p: d[id].usd, v: d[id].usd_24h_change || 0 };
    } catch (e) { if (!Object.keys(precos).length) falar(FRASES[lang].off); }
    atualizar();
  }
  function atualizar() {
    const x = precos[est.moeda];
    if (x) { est.preco = x.p; est.var = x.v; est.humor = x.v > 2 ? "moon" : x.v < -2 ? "rekt" : "garimpando"; }
    painel();
    if (Date.now() - est.frase_t > 9000) { falar(); est.frase_t = Date.now(); }
  }
  async function bloco() {
    try {
      const [h, fees] = await Promise.all([
        fetch("https://mempool.space/api/blocks/tip/height").then(r => r.text()),
        fetch("https://mempool.space/api/v1/fees/recommended").then(r => r.json())]);
      const n = parseInt(h, 10);
      if (est.bloco && n > est.bloco) { est.pulo = 8; falar(FRASES[lang].bloco(n)); est.frase_t = Date.now(); }
      est.bloco = n;
      $("#p-bloco").textContent = `#${n.toLocaleString("pt-BR")}`;
      $("#p-fee").textContent = `fee ${fees.halfHourFee} sat/vB`;
    } catch (e) { $("#p-bloco").textContent = "#?"; }
  }
  $$("[data-moeda]").forEach(b => b.onclick = () => {
    $$("[data-moeda]").forEach(x => x.classList.toggle("ativo", x === b));
    est.moeda = b.dataset.moeda; est.frase_t = 0; atualizar();
  });
  $$("[data-humor]").forEach(b => b.onclick = () => {
    $$("[data-humor]").forEach(x => x.classList.toggle("ativo", x === b));
    est.forcado = b.dataset.humor === "auto" ? null : b.dataset.humor; falar(); est.frase_t = Date.now();
  });
  $('[data-humor="auto"]').classList.add("ativo");

  // ---------- ranking ----------
  let rank = null, rankErro = false;
  const RTXT = { pt: { off: "servidor de ranking offline — o bicho continua feliz.", soon: "ranking em breve 🥚",
                       vazio: "ninguém ainda. seja o satoshi." },
                 en: { off: "leaderboard server offline — the pet is still happy.", soon: "leaderboard coming soon 🥚",
                       vazio: "nobody yet. be satoshi." } };
  function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function rankRender() {
    const tb = $("#tab-rank tbody"), t = RTXT[lang];
    if (!rank || !rank.length) {
      tb.innerHTML = `<tr><td colspan="5" class="centro" id="rank-msg">${!C.rankingUrl ? t.soon : rankErro ? t.off : rank ? t.vazio : "..."}</td></tr>`;
      return;
    }
    tb.innerHTML = rank.map(j => `<tr><td>${j.pos}</td><td>${esc(j.nick)}</td><td>${j.nivel}</td><td>${esc(j.estagio)}</td><td>${j.blocos}</td></tr>`).join("");
  }
  async function ranking() {
    if (!C.rankingUrl) return rankRender();
    try {
      const r = await fetch(C.rankingUrl.replace(/\/$/, "") + "/api/top?n=50", { cache: "no-store" });
      rank = (await r.json()).top; rankErro = false;
    } catch (e) { rankErro = true; rank = null; }
    rankRender();
  }

  aplicarLang(); mercado(); bloco(); ranking();
  setInterval(mercado, 60000); setInterval(bloco, 30000); setInterval(ranking, 120000);
})();
