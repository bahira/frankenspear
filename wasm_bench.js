'use strict';
/* Honest micro-bench: spear-kernels WASM vs JS.
   modes per kernel:
     importheavy  — package wasmBase64 + full env imports (showcase-style)
     freestanding — hand-encoded 0-import f64 WASM (build_wasm_freestanding.js)
     js_pkg       — package's own JS expression (same formula as importheavy)
     js_alu       — JS twin of the freestanding formula (same op order)
   Isolation (two independent sources of contamination, both measured):
   1) several cells in one process → V8 deopts closures sharing a
      SharedFunctionInfo ("wrong call target"/"wrong feedback cell"), up to 8x;
    2) runner shape → factory-returned runners / arrays passed as parameters
       stay deoptimized (20-100x on every kernel, fresh process), while a
       top-level `function run(n)` closing over top-level consts reaches
       TurboFan (branch-light JS ALU kernels 1.6-3.5 ns).
   Hence every cell = its own generated `node -e` script with shape (2),
   and each cell is measured twice (best p50 wins; OS noise on this box).
   p50/p99 = percentiles over `samples` batch means, each batch = `n` iters.
   Usage: node wasm_bench.js [--n 100000] [--samples 100] [--warmup 5] [--passes 2]
          [--out wasm_bench_report.json] [--kernels silu,gelu,...]          */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { FREESTANDING, JS_ALU, KERNEL_IDS, FORMULA_MAP } = require('./build_wasm_freestanding.js');
const pkg = require('spear-kernels');

const ENV_SRC = '{erf(x){const s=x<0?-1:1,ax=Math.abs(x),t=1/(1+0.3275911*ax);' +
  'return s*(1-((((1.061405429*t-1.453152027)*t+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-ax*ax));},' +
  'exp:Math.exp,sin:Math.sin,cos:Math.cos,tanh:Math.tanh,atan:Math.atan,asin:Math.asin,' +
  'sqrt:Math.sqrt,log:Math.log,abs:Math.abs,min:Math.min,max:Math.max,fmin:Math.min,fmax:Math.max,' +
  'floor:Math.floor,ceil:Math.ceil,pow:Math.pow,copysign:(m,s)=>Math.sign(s)*Math.abs(m)}';
const ENV = eval('(' + ENV_SRC + ')');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}
const N = Number(arg('n', 100000));
const SAMPLES = Number(arg('samples', 100));
const WARMUP = Number(arg('warmup', 5));
const PASSES = Number(arg('passes', 2));
const OUT = arg('out', 'wasm_bench_report.json');
const ONLY = arg('kernels', null);
const IDS = ONLY ? ONLY.split(',') : KERNEL_IDS;
const MODES = ['js_alu', 'js_pkg', 'freestanding', 'importheavy'];

// ---------- shared primitives (parent uses makeArgs for verification) ----------

function makeArgs(nArgs, len = 4096) {
  let s = 0x2545f491 >>> 0;
  const rnd = () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return (s / 4294967296) * 12 - 6; // [-6, 6)
  };
  const args = [];
  for (let a = 0; a < nArgs; a++) args.push(new Float64Array(len));
  for (let i = 0; i < len; i++) for (let a = 0; a < nArgs; a++) args[a][i] = rnd();
  return args;
}

// ---------- cell script generation ----------

function fPlan(id, mode) {
  const K = pkg.kernels[id];
  if (!K) throw new Error('unknown kernel ' + id);
  const slot = K.precise ? 'precise' : 'fast';
  const fallback = (fn) => fn.length || (id === 'concurrence_pure' ? 4 : 1);

  if (mode === 'js_alu') {
    const fn = JS_ALU[id];
    if (!fn) return null;
    return {
      arity: fallback(fn),
      needBuild: true,
      f: `const f=BUILD.JS_ALU[${JSON.stringify(id)}];`,
    };
  }
  if (mode === 'js_pkg') {
    let fn = null;
    try { fn = new Function('return(' + K[slot].js + ')')(); } catch { return null; }
    if (!fn) return null;
    return {
      arity: fallback(fn),
      needBuild: false,
      f: `const f=new Function('return('+${JSON.stringify(K[slot].js)}+')')();`,
    };
  }
  if (mode === 'freestanding') {
    const bytes = FREESTANDING[id];
    const fn = new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports.spear;
    const b64 = Buffer.from(bytes).toString('base64');
    return {
      arity: fallback(fn),
      needBuild: false,
      f: `const f=new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(${JSON.stringify(b64)},'base64'))).exports.spear;`,
    };
  }
  if (mode === 'importheavy') {
    const b64 = K[slot].wasmBase64;
    const fn = new WebAssembly.Instance(
      new WebAssembly.Module(Buffer.from(b64, 'base64')), { env: ENV }
    ).exports.spear;
    return {
      arity: fallback(fn),
      needBuild: false,
      f: `const ENV=${ENV_SRC};` +
        `const f=new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(${JSON.stringify(b64)},'base64')),{env:ENV}).exports.spear;`,
    };
  }
  throw new Error('unknown mode ' + mode);
}

function cellSource(plan, n, samples, warmup) {
  let decls, loop;
  if (plan.arity === 1) {
    decls = 'const ARGS=makeArgs(1);\nconst A0=ARGS[0];';
    loop = 'for(let i=0;i<n;i++)acc+=f(A0[i&mask]);';
  } else if (plan.arity === 4) {
    decls = 'const ARGS=makeArgs(4);\nconst A0=ARGS[0],A1=ARGS[1],A2=ARGS[2],A3=ARGS[3];';
    loop = 'for(let i=0;i<n;i++)acc+=f(A0[i&mask],A1[i&mask],A2[i&mask],A3[i&mask]);';
  } else {
    throw new Error('unsupported arity ' + plan.arity);
  }
  const req = plan.needBuild
    ? `const BUILD=require(${JSON.stringify(path.join(__dirname, 'build_wasm_freestanding.js'))});`
    : '';
  return `'use strict';
const N=${n}, SAMPLES=${samples}, WARMUP=${warmup};
${req}
function makeArgs(nArgs,len=4096){let s=0x2545f491>>>0;
const rnd=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return (s/4294967296)*12-6;};
const out=[];for(let a=0;a<nArgs;a++)out.push(new Float64Array(len));
for(let i=0;i<len;i++)for(let a=0;a<nArgs;a++)out[a][i]=rnd();
return out;}
${plan.f}
${decls}
const mask=4095;
function run(n){let acc=0;${loop}return acc;}
let sink=0;
for(let w=0;w<WARMUP;w++)sink+=run(N);
const T=[];
for(let i=0;i<SAMPLES;i++){
const t0=process.hrtime.bigint();
sink+=run(N);
const t1=process.hrtime.bigint();
T.push(Number(t1-t0)/N);
}
T.sort((x,y)=>x-y);
const q=t=>T[Math.max(0,Math.min(T.length-1,Math.ceil(t*T.length)-1))];
let sum=0;for(let i=0;i<T.length;i++)sum+=T[i];
console.log(JSON.stringify({p50_ns:q(0.5),p99_ns:q(0.99),mean_ns:sum/T.length,min_ns:T[0],max_ns:T[T.length-1],samples:T.length,n_per_sample:N,checksum:sink}));
`;
}

function spawnCell(id, mode) {
  const plan = fPlan(id, mode);
  if (!plan) return { skip: true };
  const src = cellSource(plan, N, SAMPLES, WARMUP);
  const r = spawnSync(process.execPath, ['-e', src], { encoding: 'utf8', cwd: __dirname });
  if (r.status !== 0) throw new Error(`cell ${id}/${mode} failed (exit ${r.status}): ${r.stderr}`);
  return JSON.parse(r.stdout.trim().split('\n').pop());
}

// ---------- parent: verification ----------

async function verifyFreestanding() {
  const out = {};
  for (const id of KERNEL_IDS) {
    const res = await WebAssembly.instantiate(FREESTANDING[id]); // NO import object
    const fn = res.instance.exports.spear;
    const js = JS_ALU[id];
    let maxRel = 0, maxAbs = 0;
    if (id === 'concurrence_pure') {
      const [a, d, b, c] = makeArgs(4, 2048);
      for (let i = 0; i < 2048; i++) {
        const w = fn(a[i], d[i], b[i], c[i]), j = js(a[i], d[i], b[i], c[i]);
        maxRel = Math.max(maxRel, Math.abs(w - j) / Math.max(1e-12, Math.abs(j)));
        maxAbs = Math.max(maxAbs, Math.abs(w - j));
      }
    } else {
      for (let x = -6; x <= 6.0001; x += 0.001) {
        const w = fn(x), j = js(x);
        maxRel = Math.max(maxRel, Math.abs(w - j) / Math.max(1e-12, Math.abs(j)));
        maxAbs = Math.max(maxAbs, Math.abs(w - j));
      }
    }
    out[id] = {
      instantiate_no_args: true,
      import_count: 0,
      export: 'spear',
      arity: fn.length,
      max_rel_err: maxRel,
      max_abs_err: maxAbs,
      ok: maxRel < 1e-5,
    };
    if (!out[id].ok) throw new Error(`verify failed: ${id} max_rel_err=${maxRel}`);
  }
  return out;
}

async function scanPackage() {
  const bench = new Set(KERNEL_IDS);
  const zero = [], heavy = {};
  for (const id of Object.keys(pkg.kernels)) {
    for (const slot of ['precise', 'fast']) {
      const s = pkg.kernels[id][slot];
      if (!s) continue;
      const mod = new WebAssembly.Module(Buffer.from(s.wasmBase64, 'base64'));
      const im = WebAssembly.Module.imports(mod);
      if (im.length === 0) {
        await WebAssembly.instantiate(mod);
        zero.push(id + '.' + slot);
      } else if (bench.has(id) && slot === 'precise') {
        heavy[id] = im.map((x) => x.module + '.' + x.name);
      }
    }
  }
  return { zero_import_slots: zero, bench_kernel_imports: heavy };
}

function fmtSp(x) {
  return x == null ? 'n/a' : x.toFixed(2) + 'x';
}

async function main() {
  console.log(`wasm_bench  n=${N} samples=${SAMPLES} warmup=${WARMUP} passes=${PASSES}  node=${process.version}`);
  const verification = await verifyFreestanding();
  console.log('verify: 6/6 freestanding modules instantiate with no args, max rel err < 1e-5  OK');
  const scan = await scanPackage();
  console.log(`package: ${scan.zero_import_slots.length} slot(s) already 0-import (see report)`);

  const results = {};
  let checksum = 0;
  for (const id of IDS) {
    const K = pkg.kernels[id];
    if (!K) throw new Error('unknown kernel ' + id);
    const slot = K.precise ? 'precise' : 'fast';
    const imports = WebAssembly.Module.imports(
      new WebAssembly.Module(Buffer.from(K[slot].wasmBase64, 'base64'))
    ).map((x) => x.module + '.' + x.name);

    const modes = {};
    for (const m of MODES) {
      const runs = [];
      for (let p = 0; p < PASSES; p++) runs.push(spawnCell(id, m));
      const live = runs.filter((r) => !r.skip).sort((a, b) => a.p50_ns - b.p50_ns);
      if (!live.length) {
        modes[m] = null;
        console.log(`  ${id}/${m}: skip`);
      } else {
        modes[m] = { ...live[0], passes_p50_ns: live.map((r) => r.p50_ns) };
        checksum += live[0].checksum;
        console.log(`  ${id}/${m}: p50 ${modes[m].p50_ns.toFixed(2)} ns (passes ${live.map((r) => r.p50_ns.toFixed(2)).join(', ')})`);
      }
    }
    const p = (m) => (modes[m] ? modes[m].p50_ns : null);
    const div = (a, b) => (a && b ? a / b : null);
    results[id] = {
      slot,
      imports,
      formula_freestanding: FORMULA_MAP[id],
      modes,
      speedups: {
        freestanding_vs_js_alu: div(p('js_alu'), p('freestanding')),
        importheavy_vs_js_pkg: div(p('js_pkg'), p('importheavy')),
        importheavy_vs_js_alu: div(p('js_alu'), p('importheavy')),
      },
    };
    console.log('done:', id);
  }

  console.log('');
  const pad = (s, w) => String(s).padEnd(w);
  console.log(pad('kernel', 18) + pad('mode', 14) + 'p50 ns'.padStart(10) + 'p99 ns'.padStart(10) + 'mean ns'.padStart(10));
  console.log('-'.repeat(62));
  for (const id of IDS) {
    const r = results[id];
    for (const m of MODES) {
      const s = r.modes[m];
      console.log(
        pad(id, 18) + pad(m, 14) +
        (s ? s.p50_ns.toFixed(3).padStart(10) + s.p99_ns.toFixed(3).padStart(10) + s.mean_ns.toFixed(3).padStart(10) : '-'.padStart(30))
      );
    }
    const sp = r.speedups;
    console.log(
      '  speedup: free/js_alu ' + fmtSp(sp.freestanding_vs_js_alu) +
      ' · import/js_pkg ' + fmtSp(sp.importheavy_vs_js_pkg) +
      ' · import/js_alu ' + fmtSp(sp.importheavy_vs_js_alu)
    );
    console.log('');
  }

  const med = (arr) => {
    const v = arr.filter((x) => x != null).sort((a, b) => a - b);
    if (!v.length) return null;
    return v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
  };
  const spHeavyPkg = med(IDS.map((id) => results[id].speedups.importheavy_vs_js_pkg));
  const spHeavyAlu = med(IDS.map((id) => results[id].speedups.importheavy_vs_js_alu));
  const spFree = med(IDS.map((id) => results[id].speedups.freestanding_vs_js_alu));

  const verdict = {
    median_importheavy_vs_js_pkg: spHeavyPkg,
    median_importheavy_vs_js_alu: spHeavyAlu,
    median_freestanding_vs_js_alu: spFree,
    current_package_wasm_advantageous: spHeavyPkg != null ? spHeavyPkg > 1.05 : null,
    statement:
      spHeavyPkg == null ? 'insufficient data'
      : spHeavyPkg > 1.05
        ? `import-heavy package WASM is ${spHeavyPkg.toFixed(2)}x faster than its own JS (median) — advantageous`
        : `import-heavy package WASM is ${(1 / spHeavyPkg).toFixed(2)}x SLOWER than its own JS (median ${spHeavyPkg.toFixed(2)}x) — env host-import overhead dominates; 0-import freestanding WASM is ${spFree != null ? spFree.toFixed(2) + 'x vs JS ALU' : 'n/a'}.`,
  };

  const report = {
    meta: {
      date: new Date().toISOString(),
      node: process.version,
      platform: process.platform,
      arch: process.arch,
      n_per_sample: N,
      samples: SAMPLES,
      warmup_batches: WARMUP,
      passes: PASSES,
      isolation: 'one generated `node -e` script per cell per pass (fresh process + proven runner shape); reported run = pass with lowest p50',
      iteration_basis: 'p50/p99 over per-iteration means of batches (ns/iter)',
      input_range: '[-6, 6), 4096-value LCG ring buffer',
      checksum_sink: checksum,
      command: 'node wasm_bench.js',
    },
    results,
    verification,
    package_scan: scan,
    verdict,
    notes: [
      'importheavy = package kernels[id].precise wasmBase64 + full env imports (exp/erf/tanh/...), exactly like showcase.html: every env.* call is a WASM→JS host transition, so showcase 1e6 timings measure host round-trips, not WASM compute.',
      'js_pkg = the package\'s own JS expression for the same slot → apples-to-apples speedup importheavy_vs_js_pkg isolates host-import + call overhead.',
      'freestanding = hand-encoded 0-import f64 modules (no import section at all); js_alu = same formula in JS with same op order → freestanding_vs_js_alu is the pure WASM-vs-JS comparison.',
      'Formula mismatch caveat: for silu/gelu/sigmoid/gaussian_cdf the package precise slot uses exp/erf (env imports) while freestanding/js_alu use the ALU fast-champion forms from intuition.py (see formula_freestanding) — importheavy_vs_js_alu is indicative only.',
      'tanh_sat and concurrence_pure compare like-for-like across modes (pade vs Math.tanh on the js_pkg side; concurrence exact on both sides).',
      'Harness: measuring several cells in one process deopted shared runner loops (V8 "wrong call target"/"wrong feedback cell"), and factory-returned runners / param-array runners stayed deoptimized (20-100x) even alone — each cell is therefore its own generated node -e script with a top-level function run(n) closing over top-level consts (TurboFan: branch-light kernels gaussian/sigmoid/concurrence measure 1.6-3.5 ns).',
      'Input-pattern effect (measured, interleaved A/B): on random LCG tables, branch-light JS kernels are unaffected while branchy JS Math.max/Math.min clips (silu/gelu/tanh) take ~50% branch mispredicts — p50 rises ~3x versus a sorted-pattern table. WASM freestanding encodes the same clips as branchless f64.min/f64.max, so on random inputs this real implementation difference favours WASM; all four modes of a kernel read the identical LCG ring, so ratios stay comparable.',
      'Sync instantiation uses new WebAssembly.Instance (this Node 24.13 build exposes no WebAssembly.instantiateSync).',
      'Noise: each cell measured in 2 independent passes, report keeps the lower p50 (transient OS load on this box moves p50 by up to ~7x); both p50s are in modes[*].passes_p50_ns.',
      'Dead-code elim avoided: every batch result accumulates into a checksum printed in the JSON (meta.checksum_sink = sum over reported runs). No npm deps, showcase.html untouched.',
    ],
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log('verdict:', verdict.statement);
  console.log('report →', OUT, '| checksum', checksum);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
