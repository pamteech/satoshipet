// extension.js - SatoshiPet no VS Code. Zero dependências, zero conta, zero chave.
// 1) tenta a API local do app desktop (127.0.0.1:8737/status) -> nome, humor, nível, preço
// 2) se o app não estiver rodando, pega o preço direto da CoinGecko (pública, sem chave)
// Barra de status: "⛏ BTC $97.000 +1,2%". Clique abre um painel com o sprite animado.
const vscode = require("vscode");
const path = require("path");

const IDS = { BTC: "bitcoin", ETH: "ethereum", SOL: "solana", DOGE: "dogecoin", PEPE: "pepe" };
const EMOJI = { moon: "🚀", rekt: "💀", garimpando: "⛏" };
const LINHA = { garimpando: 0, moon: 1, rekt: 2, pulo: 3 };
let barra, painel, timer, ultimo = null, ref = {};

function cfg() { return vscode.workspace.getConfiguration("satoshipet"); }

async function buscarJSON(url, ms = 6000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctrl.signal, headers: { "User-Agent": "SatoshiPet-VSCode/1.4" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}

function humorPor(v) { return v >= 2 ? "moon" : v <= -2 ? "rekt" : "garimpando"; }

async function atualizar() {
  let s = null;
  const api = cfg().get("apiLocal");
  if (/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(api)) {   // só local, nunca um host qualquer
    try { s = await buscarJSON(api + "/status", 2000); s.fonte = "app"; } catch (e) { s = null; }
  }
  if (!s) {
    const moeda = cfg().get("moeda") || "BTC";
    try {
      const j = await buscarJSON(`https://api.coingecko.com/api/v3/simple/price?ids=${IDS[moeda]}&vs_currencies=usd&include_24hr_change=true`);
      const d = j[IDS[moeda]];
      s = { nome: moeda, moeda, preco: d.usd, variacao_pct: d.usd_24h_change || 0, nivel: "?",
            estagio: "", fonte: "coingecko" };
      s.humor = humorPor(s.variacao_pct);
      s.preco_fmt = "$" + (d.usd >= 1 ? d.usd.toLocaleString("pt-BR", { maximumFractionDigits: 2 }) : d.usd.toPrecision(3));
    } catch (e) {
      barra.text = "$(debug-disconnect) satoshipet offline";
      return;
    }
  }
  ultimo = s;
  const v = Number(s.variacao_pct || 0);
  barra.text = `${EMOJI[s.humor] || "⛏"} ${s.moeda} ${s.preco_fmt} ${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
  barra.tooltip = `${s.nome} · LV${s.nivel} ${s.estagio || ""} · fonte: ${s.fonte === "app" ? "app desktop" : "CoinGecko"}\nclique pra abrir o bicho`;
  if (painel) painel.webview.postMessage({ tipo: "status", s });
}

function html(webview, ctx) {
  const sprites = {};
  for (const m of Object.keys(IDS)) {
    sprites[m] = webview.asWebviewUri(vscode.Uri.file(path.join(ctx.extensionPath, "media", `${m}_padrao.png`))).toString();
  }
  const csp = `default-src 'none'; img-src ${webview.cspSource}; style-src 'unsafe-inline'; script-src 'nonce-tama';`;
  return `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${csp}">
<style>
body{background:#1a1c2c;color:#f4f4f4;font:14px monospace;display:flex;flex-direction:column;align-items:center;padding:16px}
#s{width:192px;height:192px;background-repeat:no-repeat;background-size:768px 768px;image-rendering:pixelated;cursor:pointer}
.n{color:#ffcd75;font-size:18px;margin-top:8px}.moon{color:#38b764}.rekt{color:#b13e53}.garimpando{color:#ef7d57}
small{color:#566c86;margin-top:12px}
</style></head><body>
<div id="s" title="carinho!"></div><div class="n" id="n">...</div><div id="p"></div><div id="h"></div>
<small>SatoshiPet · não é conselho financeiro</small>
<script nonce="tama">
const SPR=${JSON.stringify(sprites)},L=${JSON.stringify(LINHA)};let s={moeda:"BTC",humor:"garimpando"},f=0,pulo=0;
const el=document.getElementById("s");
function d(){const linha=pulo>0?"pulo":s.humor;el.style.backgroundImage="url("+SPR[s.moeda]+")";
el.style.backgroundPosition=(-f*192)+"px "+(-(L[linha]||0)*192)+"px";f=(f+1)%4;if(pulo)pulo--;}
setInterval(d,180);el.onclick=()=>{pulo=8;};
window.addEventListener("message",e=>{if(e.data.tipo==="status"){s=e.data.s;
document.getElementById("n").textContent=s.nome+(s.nivel!=="?"?" · LV"+s.nivel:"");
const v=Number(s.variacao_pct||0);document.getElementById("p").innerHTML=s.moeda+" "+s.preco_fmt+
' <span class="'+s.humor+'">'+(v>=0?"+":"")+v.toFixed(2)+"%</span>";
document.getElementById("h").className=s.humor;document.getElementById("h").textContent=s.humor.toUpperCase();}});
</script></body></html>`;
}

function activate(ctx) {
  barra = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  barra.command = "satoshipet.abrir";
  barra.text = "⛏ satoshipet...";
  barra.show();
  ctx.subscriptions.push(barra);
  ctx.subscriptions.push(vscode.commands.registerCommand("satoshipet.abrir", () => {
    if (painel) { painel.reveal(); return; }
    painel = vscode.window.createWebviewPanel("satoshipet", "SatoshiPet", vscode.ViewColumn.Beside,
      { enableScripts: true, localResourceRoots: [vscode.Uri.file(path.join(ctx.extensionPath, "media"))] });
    painel.webview.html = html(painel.webview, ctx);
    painel.onDidDispose(() => { painel = null; });
    if (ultimo) setTimeout(() => painel && painel.webview.postMessage({ tipo: "status", s: ultimo }), 300);
  }));
  ctx.subscriptions.push(vscode.commands.registerCommand("satoshipet.carinho", () => {
    vscode.window.showInformationMessage(["hehe, cosquinha!", "HODL e carinho, a única estratégia", "gm, fren!"][Math.floor(Math.random() * 3)]);
  }));
  atualizar();
  timer = setInterval(atualizar, Math.max(20, cfg().get("intervaloSeg") || 60) * 1000);
}

function deactivate() { if (timer) clearInterval(timer); }

module.exports = { activate, deactivate, _humorPor: humorPor };
