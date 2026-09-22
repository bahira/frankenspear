'use strict';
/* Batch WASM vs JS loop: one WASM call maps f over N f64s
   (run(i32 ptr, i32 n), in-place, 0-import, shared module memory),
   amortizing the JS<->WASM boundary that made scalar freestanding
   lose to JS ALU (~0.24x, wasm_bench_report.json).
   Same ALU-fast formulas as build_wasm_freestanding.js (JS_ALU twins),
   same LCG input [-6,6), N in {256, 4096, 65536, 1e6}.
   One `node -e` cell per (kernel, N, mode, pass) — the isolation shape
   proven in wasm_bench.js; best p50 pass wins. Warmup + checksum
   anti-DCE + >=2 passes. Correctness: batch wasm vs JS < 1e-4 rel.
   Usage: node wasm_batch_bench.js [--passes 2] [--out wasm_batch_report.json]
                                                [--kernels sigmoid,gelu,...] */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { JS_ALU, FORMULA_MAP, uleb, f64c, sec, vec } = require('./build_wasm_freestanding.js');

// ---------- batch encoder (reuses uleb/f64c/sec/vec from build_wasm_freestanding) ----------

const G = (i) => [0x20, ...uleb(i)]; // local.get
const S = (i) => [0x21, ...uleb(i)]; // local.set
const I32 = (n) => [0x41, ...uleb(n)]; // i32.const, n >= 0 only
const LD = [0x2b, 0x03, 0x00]; // f64.load align=3 offset=0
const ST = [0x39, 0x03, 0x00]; // f64.store
const ADD = [0xa0], SUB = [0xa1], MUL = [0xa2], DIV = [0xa3];
const ABS = [0x99], MAX = [0xa5], MIN = [0xa4];
const I32ADD = [0x6a], I32MUL = [0x6c], GE_S = [0x4e];
const C = f64c;
const T = 3; // f64 local holding x (params 0,1; i32 local 2; f64 locals 3..)

function addr() { return [...G(0), ...G(2), ...I32(8), ...I32MUL, ...I32ADD]; }

function reluAffineElem(a, cNeg, t = T) {
  return [...G(t), ...C(0), ...MAX, ...C(a), ...MUL, ...C(cNeg), ...SUB];
}
function ratAbsElem(a, b, d, t = T) {
  return [...G(t), ...G(t), ...ABS, ...C(b), ...ADD, ...DIV, ...C(a), ...MUL, ...C(d), ...ADD];
}
function padeElem(t = 3, y = 4, y2 = 5, y3 = 6, y4 = 7) {
  return [
    ...G(t), ...C(-4), ...MAX, ...C(4), ...MIN, ...S(y),
    ...G(y), ...G(y), ...MUL, ...S(y2),
    ...G(y2), ...G(y), ...MUL, ...S(y3),
    ...G(y2), ...G(y2), ...MUL, ...S(y4),
    ...G(y), ...C(0.994894946), ...MUL,
    ...G(y3), ...C(0.076611228), ...MUL, ...ADD,
    ...C(1),
    ...G(y2), ...C(0.402171314), ...MUL, ...ADD,
    ...G(y4), ...C(0.005670342), ...MUL, ...ADD,
    ...DIV,
  ];
}

// module: type (i32,i32)->(), 0 imports, memory 125 pages (8MB >= 1e6 f64),
// exports run + memory; loop: t=load(ptr+i*8); store(ptr+i*8, f(t))
function buildBatch(nF64, elem) {
  const type = [0x60, 0x02, 0x7f, 0x7f, 0x00];
  const decls = [0x02, 0x01, 0x7f, ...uleb(nF64), 0x7c]; // 1 i32 (i), nF64 f64
  const code = [
    ...I32(0), ...S(2), ...[0x02, 0x40], ...[0x03, 0x40],
        ...G(2), ...G(1), ...GE_S, ...[0x0d, 0x01], // i >= n -> exit
        ...addr(), ...LD, ...S(3), // t = x
        ...addr(), ...elem, ...ST, // store f(t)
        ...G(2), ...I32(1), ...I32ADD, ...S(2), // i++
        ...[0x0c, 0x00], // br loop
        ...[0x0b], ...[0x0b],
  ];
  const body = [...decls, ...code, 0x0b];
  const sized = [...uleb(body.length), ...body];
  return Uint8Array.from([
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
    ...sec(1, vec([type])),
    ...sec(3, vec([[0]])),
    ...sec(5, vec([[0x00, ...uleb(125)]])),
    ...sec(7, vec([
      [0x03, 0x72, 0x75, 0x6e, 0x00, 0x00],
      [0x06, 0x6d, 0x65, 0x6d, 0x6f, 0x72, 0x79, 0x02, 0x00],
    ])),
    ...sec(10, vec([sized])),
  ]);
}

const BATCH_KERNELS = {
  silu: buildBatch(1, reluAffineElem(1.016356, 0.15849)),
  gelu: buildBatch(1, reluAffineElem(1.010719, 0.057684)),
  gaussian_cdf: buildBatch(1, ratAbsElem(0.625605, 0.912761, 0.5)),
  sigmoid: buildBatch(1, ratAbsElem(0.605014, 1.24384, 0.5)),
  tanh_sat: buildBatch(5, padeElem()),
};
const IDS = Object.keys(BATCH_KERNELS);
const NS = [256, 4096, 65536, 1e6];

// ---------- CLI ----------

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}
const PASSES = Number(arg('passes', 2));
const OUT = arg('out', 'wasm_batch_report.json');
const ONLY = arg('kernels', null);
const KEYS = ONLY ? ONLY.split(',') : IDS;

const MAKE_SRC = `function makeSrc(N){let s=0x2545f491>>>0;const a=new Float64Array(N);
for(let i=0;i<N;i++){s=(Math.imul(s,1664525)+1013904223)>>>0;a[i]=(s/4294967296)*12-6;}return a;}`;

const TAIL = (n) => `T.sort((x,y)=>x-y);
const q=t=>T[Math.max(0,Math.min(T.length-1,Math.ceil(t*T.length)-1))];
let sum=0;for(let i=0;i<${n};i++)sum+=B[i];
console.log(JSON.stringify({p50_ns:q(0.5),p99_ns:q(0.99),min_ns:T[0],max_ns:T[T.length-1],samples:T.length,n:${n},checksum:sum}));`;

function samplesFor(N) { return Math.max(50, Math.min(500, Math.ceil(2e6 / N))); }
const WARMUP = 5;

function jsCell(id, N) {
  const S = samplesFor(N);
  return `'use strict';
const N=${N};
const BUILD=require(${JSON.stringify(path.join(__dirname, 'build_wasm_freestanding.js'))});
const f=BUILD.JS_ALU[${JSON.stringify(id)}];
${MAKE_SRC}
const SRC=makeSrc(N);
const B=new Float64Array(N);
function run(){for(let i=0;i<N;i++)B[i]=f(B[i]);}
for(let w=0;w<${WARMUP};w++){B.set(SRC);run();}
const T=[];
for(let s=0;s<${S};s++){B.set(SRC);const t0=process.hrtime.bigint();run();const t1=process.hrtime.bigint();T.push(Number(t1-t0));}
${TAIL(N)}
`;
}

function wasmCell(id, N) {
  const S = samplesFor(N);
  const b64 = Buffer.from(BATCH_KERNELS[id]).toString('base64');
  return `'use strict';
const N=${N};
const inst=new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(${JSON.stringify(b64)},'base64')));
const run=inst.exports.run;
const B=new Float64Array(inst.exports.memory.buffer);
${MAKE_SRC}
const SRC=makeSrc(N);
if(B.length<N)throw new Error('wasm memory too small');
function reset(){B.set(SRC);}
for(let w=0;w<${WARMUP};w++){reset();run(0,N);}
const T=[];
for(let s=0;s<${S};s++){reset();const t0=process.hrtime.bigint();run(0,N);const t1=process.hrtime.bigint();T.push(Number(t1-t0));}
${TAIL(N)}
`;
}

function spawnCell(id, mode, N) {
  const src = mode === 'wasm' ? wasmCell(id, N) : jsCell(id, N);
  const r = spawnSync(process.execPath, ['-e', src], { encoding: 'utf8', cwd: __dirname });
  if (r.status !== 0) throw new Error(`cell ${id}/${mode}/N=${N} failed (exit ${r.status}): ${r.stderr}`);
  return JSON.parse(r.stdout.trim().split('\n').pop());
}

// ---------- verification: batch wasm output vs JS_ALU, same inputs ----------

function makeSrc(N) {
  let s = 0x2545f491 >>> 0;
  const a = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    a[i] = (s / 4294967296) * 12 - 6;
  }
  return a;
}

function verify() {
  const out = {};
  const N = 4096;
  for (const id of IDS) {
    const inst = new WebAssembly.Instance(new WebAssembly.Module(BATCH_KERNELS[id]));
    const mem = new Float64Array(inst.exports.memory.buffer);
    const src = makeSrc(N);
    mem.set(src);
    inst.exports.run(0, N);
    const f = JS_ALU[id];
    let maxRel = 0, maxAbs = 0;
    for (let i = 0; i < N; i++) {
      const w = mem[i], j = f(src[i]);
      const d = Math.abs(w - j);
      if (d > maxAbs) maxAbs = d;
      const r = d / Math.max(1e-12, Math.abs(j));
      if (r > maxRel) maxRel = r;
    }
    out[id] = { n: N, max_rel_err: maxRel, max_abs_err: maxAbs, ok: maxRel < 1e-4 };
    if (!out[id].ok) throw new Error(`verify failed: ${id} max_rel_err=${maxRel}`);
  }
  return out;
}

const fmtSp = (x) => (x == null ? 'n/a' : x.toFixed(2) + 'x');

function main() {
  console.log(`wasm_batch_bench  passes=${PASSES}  node=${process.version}`);
  const verification = verify();
  console.log(`verify: ${IDS.length}/${IDS.length} batch kernels < 1e-4 rel vs JS_ALU on N=4096  OK`);

  const results = {};
  let checksum = 0;
  for (const id of KEYS) {
    const ns = {};
    for (const N of NS) {
      const modes = {};
      for (const mode of ['wasm', 'js']) {
        const runs = [];
        for (let p = 0; p < PASSES; p++) runs.push(spawnCell(id, mode, N));
        runs.sort((a, b) => a.p50_ns - b.p50_ns);
        modes[mode] = { ...runs[0], passes_p50_ns: runs.map((r) => r.p50_ns) };
        checksum += runs[0].checksum;
      }
      const wasmP50 = modes.wasm.p50_ns / N;
      const jsP50 = modes.js.p50_ns / N;
      ns[N] = {
        wasm: { p50_ns_per_elem: wasmP50, p99_ns_per_elem: modes.wasm.p99_ns / N, p50_call_ns: modes.wasm.p50_ns, passes_p50_ns: modes.wasm.passes_p50_ns },
        js: { p50_ns_per_elem: jsP50, p99_ns_per_elem: modes.js.p99_ns / N, passes_p50_ns: modes.js.passes_p50_ns },
        speedup_js_over_wasm: jsP50 / wasmP50, // >1 => batch WASM wins
        samples: modes.wasm.samples,
      };
      console.log(`  ${id.padEnd(14)} N=${String(N).padEnd(7)} wasm ${wasmP50.toFixed(3)} ns/e  js ${jsP50.toFixed(3)} ns/e  → ${fmtSp(jsP50 / wasmP50)}`);
    }
    results[id] = { formula: FORMULA_MAP[id], ns };
    console.log('done:', id);
  }

  // verdict: median speedup per N across measured kernels
  const perN = {};
  for (const N of NS) {
    const v = KEYS.map((id) => results[id].ns[N].speedup_js_over_wasm).sort((a, b) => a - b);
    perN[N] = v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
  }
  const crossover = NS.find((N) => perN[N] > 1.05) || null;

  console.log('');
  const pad = (s, w) => String(s).padEnd(w);
  console.log(pad('kernel', 14) + pad('N', 8) + 'wasm p50'.padStart(10) + 'js p50'.padStart(10) + 'wasm p99'.padStart(10) + 'js p99'.padStart(10) + 'speedup'.padStart(10));
  console.log('-'.repeat(72));
  for (const id of KEYS) {
    for (const N of NS) {
      const r = results[id].ns[N];
      console.log(
        pad(id, 14) + pad(N, 8) +
        r.wasm.p50_ns_per_elem.toFixed(3).padStart(10) +
        r.js.p50_ns_per_elem.toFixed(3).padStart(10) +
        r.wasm.p99_ns_per_elem.toFixed(3).padStart(10) +
        r.js.p99_ns_per_elem.toFixed(3).padStart(10) +
        fmtSp(r.speedup_js_over_wasm).padStart(10)
      );
    }
  }
  console.log('');
  console.log('median speedup per N: ' + NS.map((N) => `N=${N}: ${fmtSp(perN[N])}`).join('  '));

  const statement = crossover
    ? `batch WASM beats JS (>1.05x median) from N=${crossover} — boundary cost amortized.`
    : `batch WASM never beats JS ALU on this box (medians: ${NS.map((N) => fmtSp(perN[N])).join(', ')}) — boundary amortization insufficient.`;

  const report = {
    meta: {
      date: new Date().toISOString(),
      node: process.version,
      platform: process.platform,
      arch: process.arch,
      n_values: NS,
      samples_per_n: Object.fromEntries(NS.map((N) => [N, samplesFor(N)])),
      warmup_batches: WARMUP,
      passes: PASSES,
      isolation: 'one generated `node -e` script per (kernel, N, mode, pass); reported run = pass with lowest p50',
      iteration_basis: 'p50/p99 over total call times / N (ns per element); one call per sample, input refilled outside timing',
      input_range: '[-6, 6) LCG, full-length buffer per N',
      checksum_sink: checksum,
      command: 'node wasm_batch_bench.js',
    },
    results,
    verification,
    verdict: {
      median_speedup_per_n: perN,
      crossover_N: crossover,
      statement,
      batch_wasm_advantageous: crossover != null,
    },
    notes: [
      'Motivation: wasm_bench_report.json showed scalar freestanding WASM at 0.36x vs JS ALU (median) — per-call boundary dominates. Batch moves the loop inside WASM: one (ptr,n) call per buffer.',
      'Kernels = 5 ALU-fast champions, hand-encoded 0-import modules: run(i32 ptr, i32 n) in-place over module memory (125 pages), exports run+memory. JS side = same JS_ALU formula, same op order.',
      'speedup_js_over_wasm = js_p50/wasm_p50 per element; >1 means batch WASM wins.',
      'Both sides: memory/array refilled from the same LCG source outside the timer; checksum printed (anti-DCE). tanh_sat verified like the others (Padé locals y,y2,y3,y4).',
      'Integration: merge verdict + results table into the final report alongside wasm_bench_report.json (scalar) — batch vs scalar contrast is the boundary-cost story.',
      'Re-run: node wasm_batch_bench.js',
    ],
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log('verdict:', statement);
  console.log('report →', OUT, '| checksum', checksum);
}

main();
