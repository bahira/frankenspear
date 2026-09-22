const fs = require('fs');
const html = fs.readFileSync('showcase.html', 'utf8');
const km = html.match(/id="kernels">([\s\S]*?)<\/script>/);
const sm = html.match(/id="slm">([\s\S]*?)<\/script>/);
if (!km || !sm) { console.error('embed missing'); process.exit(1); }
const KERNELS = JSON.parse(km[1]);
const SLM = JSON.parse(sm[1]);
console.log('json ok', Object.keys(KERNELS).length, 'kernels; W1', SLM.W1.length + 'x' + SLM.W1[0].length);
console.log('placeholders left', html.includes('__KERNELS__') || html.includes('__SLM__'));
console.log('has wasm', html.includes('WebAssembly.instantiate'), 'router', html.includes('runRoute'), 'bench', html.includes('id="bench"'));

const ENV = {
  erf(x){ const s=x<0?-1:1, ax=Math.abs(x), t=1/(1+0.3275911*ax);
    return s*(1-((((1.061405429*t-1.453152027)*t+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-ax*ax)); },
  exp: Math.exp, sin: Math.sin, cos: Math.cos, tanh: Math.tanh, atan: Math.atan,
  asin: Math.asin, sqrt: Math.sqrt, log: Math.log, abs: Math.abs,
  min: Math.min, max: Math.max, fmin: Math.min, fmax: Math.max,
  floor: Math.floor, ceil: Math.ceil, pow: Math.pow,
  copysign: (m, s) => Math.sign(s) * Math.abs(m),
};
async function loadWasm(b64) {
  const bytes = Uint8Array.from(Buffer.from(b64, 'base64'));
  const { instance } = await WebAssembly.instantiate(bytes, { env: ENV });
  return instance.exports.spear;
}

function tanhPade(x){ x=Math.max(-4,Math.min(4,x));
  return (0.994894946*x+0.076611228*x*x*x)/(1+0.402171314*x*x+0.005670342*x*x*x*x); }
function sigmoidAlu(x){ return 0.5+0.5*tanhPade(0.5*x); }
function siluAlu(x){ return x*sigmoidAlu(x); }
function geluQuintic(x){ const t=Math.max(0,Math.min(1,0.200055340257*x+0.5));
  return x*t*t*t*(6*t*t-15*t+10)-0.01104961; }
function gaussKernel(x){ return tanhPade(0.6*x); }
function gaussianCdfFast(x){ return 0.625605*(x/(0.912761+Math.abs(x)))+0.5; }

const TOOL_RE = /(tool|bash|edit|exec|lance|exécute|execute)/;
function features(text) {
  const t = (text || '').toLowerCase();
  const words = t.split(/\s+/).filter(Boolean);
  const n = Math.max(words.length, 1);
  const match = (re, s) => ((s.match(new RegExp(re, 'g')) || []).length);
  const MATH_W = ['gelu','lorentz','kepler','math','kernel','quantum','chsh','grover','concurrence','tanh','sigmoid'];
  const CODE_W = ['écris','write','code','fonction','script'];
  const IMP = ['fais','do','lance','run','calcule','compute','ajoute','add'];
  const Q_W = ['quoi','what','comment','how','pourquoi','why','combien'];
  const TECH_W = ['api','http','json','sql','git','docker','npm','pip','debug'];
  return new Float64Array([
    Math.log1p(t.length)/5,
    match(TOOL_RE.source, t)/3,
    ((t.match(/```/g)||[]).length + (t.match(/def /g)||[]).length)/3,
    MATH_W.some(k => t.includes(k)) ? 1 : 0,
    CODE_W.some(k => t.includes(k)) ? 1 : 0,
    (t.match(/ /g)||[]).length/30,
    match('\\d+', t)/5,
    t.includes('?') ? 1 : 0,
    (t.includes('merci') || t.includes('thanks')) ? 1 : 0,
    0,
    new Set(words).size/n,
    Math.min(words.reduce((s,w)=>s+w.length,0)/n/10, 1),
    match(TOOL_RE.source, t)/5 + (IMP.some(k => t.includes(k)) ? 1 : 0),
    (Q_W.some(k => t.includes(k)) ? 1 : 0) + match('!', t)/5,
    (TECH_W.some(k => t.includes(k)) ? 1 : 0) + match('\\.\\.\\.', t)/3,
    t.split('\n').length/20,
  ]);
}
function matVec(x, W, b) {
  const d = x.length, h = W[0].length, out = new Float64Array(h);
  for (let j = 0; j < h; j++) {
    let s = b[j];
    for (let i = 0; i < d; i++) s += x[i] * W[i][j];
    out[j] = s;
  }
  return out;
}
function embTransform(x) {
  const { W, mu, sigma } = SLM;
  const d = x.length, xn = new Float64Array(d);
  for (let i = 0; i < d; i++) xn[i] = sigma[i] > 1e-5 ? (x[i]-mu[i])/sigma[i] : 0;
  const z = matVec(xn, W, new Float64Array(W[0].length));
  const acts = [siluAlu, gaussKernel, geluQuintic, tanhPade];
  const parts = [...xn];
  for (const a of acts) for (let i = 0; i < z.length; i++) parts.push(a(z[i]));
  return Float64Array.from(parts);
}
function predict(x) {
  const z = embTransform(x);
  const a = Array.from(matVec(z, SLM.W1, SLM.b1)).map(tanhPade);
  return sigmoidAlu(Array.from(matVec(Float64Array.from(a), SLM.W2, SLM.b2))[0]);
}

(async () => {
  let ok = 0, fail = 0;
  for (const id of Object.keys(KERNELS)) {
    for (const slot of ['precise', 'fast']) {
      try {
        const fn = await loadWasm(KERNELS[id][slot].wasm);
        const n = fn.length;
        const args = Array.from({ length: n }, (_, i) => (i === 0 ? 1 : 0.5));
        const v = fn(...args);
        if (n > 0 && !Number.isFinite(v)) { console.log('bad', id, slot, v); fail++; }
        else ok++;
      } catch (e) {
        console.log('fail', id, slot, e.message);
        fail++;
      }
    }
  }
  console.log('wasm smoke', ok, 'ok', fail, 'fail');

  // expected from python intuition.py (seed 42), new gate rule:
  // path = (label===0 && conf>=0.65) ? 'instant' : 'slow', label = p>=0.5?1:0
  const tests = [
    ['salut', 0.490, 0.179, 'slow'],
    ['écris une fonction gelu', 0.847, 0.686, 'slow'],
    ['exécute le bash', 0.614, 0.266, 'slow'],
    ['quantum chsh grover concurrence', 0.307, 0.375, 'slow'],
    ['quoi est-ce que tanh', 0.649, 0.308, 'slow'],
  ];
  let routerOk = true;
  for (const [text, ep, ec, epath] of tests) {
    const p = predict(features(text));
    const conf = gaussianCdfFast(4 * Math.abs(p - 0.5) - 1);
    const label = p >= 0.5 ? 1 : 0;
    const path = (label === 0 && conf >= 0.65) ? 'instant' : 'slow';
    const pass = Math.abs(p - ep) < 0.02 && Math.abs(conf - ec) < 0.02 && path === epath;
    if (!pass) routerOk = false;
    console.log(pass ? 'OK' : 'MISMATCH', JSON.stringify(text), p.toFixed(3), conf.toFixed(3), path, 'exp', ep, ec, epath);
  }
  // lr gate path (fit_lr on train split seed 42), expected from python export_lr.py
  if (SLM.lr) {
    const {mu, sd, w, b} = SLM.lr;
    console.log('lr dims', mu.length, sd.length, w.length, 'b', b.toFixed(3));
    if (mu.length !== 16 || sd.length !== 16 || w.length !== 16) { console.log('bad lr dims'); routerOk = false; }
    const lrTests = [['salut', 1.000, 'instant'], ['écris une fonction gelu', 0.996, 'instant']];
    for (const [text, ep, epath] of lrTests) {
      const f = features(text);
      let z = b;
      for (let i = 0; i < f.length; i++) z += w[i] * ((f[i] - mu[i]) / sd[i]);
      const pt = 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));
      const pth = pt >= 0.5 ? 'instant' : 'slow';
      const pass = Math.abs(pt - ep) < 0.02 && pth === epath;
      if (!pass) routerOk = false;
      console.log(pass ? 'OK' : 'MISMATCH', 'lr', JSON.stringify(text), pt.toFixed(3), pth, 'exp', ep, epath);
    }
  } else console.log('lr n/a');
  if (fail || !routerOk) process.exit(1);
  console.log('ALL GREEN');
})();
