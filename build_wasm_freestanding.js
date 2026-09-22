'use strict';
/* Hand-encoded 0-import f64 WASM modules — Spear ALU champions.
   Each module: no import section, exports `spear`, pure f64 ops only.
   JS_ALU holds the same formulas in JS (same op order) for verification.
   Run directly to emit .wasm files: node build_wasm_freestanding.js */

function uleb(n) {
  const o = [];
  n = n >>> 0;
  do {
    let b = n & 0x7f;
    n >>>= 7;
    if (n) b |= 0x80;
    o.push(b);
  } while (n);
  return o;
}

function f64c(x) {
  const b = Buffer.allocUnsafe(8);
  b.writeDoubleLE(x);
  return [0x44, ...b];
}

function sec(id, payload) {
  return [id, ...uleb(payload.length), ...payload];
}

function vec(chunks) {
  const flat = [];
  for (const c of chunks) flat.push(...c);
  return [...uleb(chunks.length), ...flat];
}

const G = (i) => [0x20, ...uleb(i)]; // local.get
const S = (i) => [0x21, ...uleb(i)]; // local.set
const C = f64c;
const ADD = [0xa0], SUB = [0xa1], MUL = [0xa2], DIV = [0xa3];
const ABS = [0x99], MAX = [0xa5], MIN = [0xa4];

function buildModule(nParams, nLocals, code) {
  const type = [0x60, ...uleb(nParams), ...Array(nParams).fill(0x7c), 0x01, 0x7c];
  const decls = nLocals ? [0x01, ...uleb(nLocals), 0x7c] : [0x00];
  const body = [...decls, ...code, 0x0b];
  const sized = [...uleb(body.length), ...body];
  return Uint8Array.from([
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
    ...sec(1, vec([type])),
    ...sec(3, vec([[0]])),
    ...sec(7, vec([[0x05, 0x73, 0x70, 0x65, 0x61, 0x72, 0x00, 0x00]])), // export "spear"
    ...sec(10, vec([sized])),
  ]);
}

// Padé[3/4] tanh: locals y,y2,y3,y4 = 1,2,3,4 of a 1-param module
function padeOn(src) {
  return [
    ...G(src), ...C(-4), ...MAX, ...C(4), ...MIN, ...S(1),
    ...G(1), ...G(1), ...MUL, ...S(2),
    ...G(2), ...G(1), ...MUL, ...S(3),
    ...G(2), ...G(2), ...MUL, ...S(4),
    ...G(1), ...C(0.994894946), ...MUL,
    ...G(3), ...C(0.076611228), ...MUL, ...ADD,
    ...C(1),
    ...G(2), ...C(0.402171314), ...MUL, ...ADD,
    ...G(4), ...C(0.005670342), ...MUL, ...ADD,
    ...DIV,
  ];
}

function padeJS(x) {
  const y = Math.max(-4, Math.min(4, x));
  const y2 = y * y, y3 = y2 * y, y4 = y2 * y2;
  return (0.994894946 * y + 0.076611228 * y3) /
    (1 + 0.402171314 * y2 + 0.005670342 * y4);
}

// a*c*x/(b+|x|)+d form  (sigmoid_fast / gaussian_cdf_fast)
function ratAbsCode(a, b, d) {
  return [
    ...G(0), ...G(0), ...ABS, ...C(b), ...ADD, ...DIV,
    ...C(a), ...MUL, ...C(d), ...ADD,
  ];
}
function ratAbsJS(a, b, d) {
  return (x) => a * (x / (b + Math.abs(x))) + d;
}
// a*relu(x)+c form (gelu_fast_relu / silu_fast_relu): wasm does max(x,0)*a then -|c|
function reluAffineCode(a, cNeg) {
  return [...G(0), ...C(0), ...MAX, ...C(a), ...MUL, ...C(cNeg), ...SUB];
}
function reluAffineJS(a, cNeg) {
  return (x) => a * Math.max(0, x) - cNeg;
}

const FREESTANDING = {
  silu: buildModule(1, 0, reluAffineCode(1.016356, 0.15849)),
  gelu: buildModule(1, 0, reluAffineCode(1.010719, 0.057684)),
  gaussian_cdf: buildModule(1, 0, ratAbsCode(0.625605, 0.912761, 0.5)),
  sigmoid: buildModule(1, 0, ratAbsCode(0.605014, 1.24384, 0.5)),
  tanh_sat: buildModule(1, 4, padeOn(0)),
  concurrence_pure: buildModule(4, 0, [
    ...G(0), ...G(1), ...MUL,
    ...G(2), ...G(3), ...MUL,
    ...SUB, ...ABS, ...C(2), ...MUL,
  ]),
};

const JS_ALU = {
  silu: reluAffineJS(1.016356, 0.15849),
  gelu: reluAffineJS(1.010719, 0.057684),
  gaussian_cdf: ratAbsJS(0.625605, 0.912761, 0.5),
  sigmoid: ratAbsJS(0.605014, 1.24384, 0.5),
  tanh_sat: padeJS,
  concurrence_pure: (a, d, b, c) => 2 * Math.abs(a * d - b * c),
};

const KERNEL_IDS = Object.keys(FREESTANDING);

const FORMULA_MAP = {
  silu: 'silu_fast_relu ALU (intuition.py) 1.016356*relu(x)-0.15849',
  gelu: 'gelu_fast_relu ALU 1.010719*relu(x)-0.057684',
  gaussian_cdf: 'gaussian_cdf_fast ALU 0.625605*x/(0.912761+|x|)+0.5',
  sigmoid: 'sigmoid_fast ALU 0.605014*x/(1.24384+|x|)+0.5',
  tanh_sat: 'tanh_pade ALU Padé[3/4] (1 div, clip ±4)',
  concurrence_pure: 'exact 2|ad-bc| (f64, no imports either side)',
};

if (require.main === module) {
  const fs = require('fs');
  const path = require('path');
  const dir = path.join(__dirname, 'wasm_freestanding');
  fs.mkdirSync(dir, { recursive: true });
  for (const id of KERNEL_IDS) {
    const file = path.join(dir, id + '.wasm');
    fs.writeFileSync(file, FREESTANDING[id]);
    console.log(id.padEnd(18), FREESTANDING[id].length, 'bytes →', path.relative(process.cwd(), file));
  }
  console.log('all 0-import, exports: spear');
}

module.exports = { FREESTANDING, JS_ALU, KERNEL_IDS, FORMULA_MAP, padeJS, uleb, f64c, sec, vec };
