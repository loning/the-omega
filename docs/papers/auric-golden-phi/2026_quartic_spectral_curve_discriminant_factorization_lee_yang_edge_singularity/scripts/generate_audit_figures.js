#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');

const PAPER_DIR = path.resolve(__dirname, '..');
const FIG_DIR = path.join(PAPER_DIR, 'figs');
const DATA_DIR = path.join(FIG_DIR, 'data');

function ensureDir(p) {
  if (!fs.existsSync(p)) {
    fs.mkdirSync(p, { recursive: true });
  }
}

function complex(re = 0, im = 0) {
  return { re, im };
}

function toComplex(v) {
  return (typeof v === 'number') ? complex(v, 0) : v;
}

function cAdd(a, b) {
  a = toComplex(a);
  b = toComplex(b);
  return complex(a.re + b.re, a.im + b.im);
}

function cSub(a, b) {
  a = toComplex(a);
  b = toComplex(b);
  return complex(a.re - b.re, a.im - b.im);
}

function cMul(a, b) {
  a = toComplex(a);
  b = toComplex(b);
  return complex(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);
}

function cDiv(a, b) {
  a = toComplex(a);
  b = toComplex(b);
  const den = b.re * b.re + b.im * b.im;
  return complex((a.re * b.re + a.im * b.im) / den, (a.im * b.re - a.re * b.im) / den);
}

function cScale(a, s) {
  a = toComplex(a);
  return complex(a.re * s, a.im * s);
}

function cAbs2(a) {
  return a.re * a.re + a.im * a.im;
}

function cAbs(a) {
  return Math.hypot(a.re, a.im);
}

function polyEval(coeff, z) {
  // coeff: descending coefficients, each coefficient may be real or complex.
  let y = toComplex(coeff[0]);
  for (let i = 1; i < coeff.length; i++) {
    y = cAdd(cMul(y, z), toComplex(coeff[i]));
  }
  return y;
}

function normalizeRoot(a) {
  if (Math.abs(a.im) < 1e-14) return complex(a.re, 0);
  return a;
}

function dist2(a, b) {
  const dx = a.re - b.re;
  const dy = a.im - b.im;
  return dx * dx + dy * dy;
}

function sortBySeed(previous, current) {
  if (!previous || previous.length === 0) return current;
  const used = new Array(current.length).fill(false);
  const ordered = new Array(current.length);
  for (let i = 0; i < previous.length; i++) {
    let best = -1;
    let bestDist = Infinity;
    for (let j = 0; j < current.length; j++) {
      if (used[j]) continue;
      const d = dist2(previous[i], current[j]);
      if (d < bestDist) {
        bestDist = d;
        best = j;
      }
    }
    if (best < 0) {
      continue;
    }
    ordered[i] = current[best];
    used[best] = true;
  }
  for (let j = 0; j < current.length; j++) {
    if (!used[j]) {
      for (let i = 0; i < ordered.length; i++) {
        if (!ordered[i]) {
          ordered[i] = current[j];
          break;
        }
      }
    }
  }
  return ordered;
}

function solvePolynomial(coeffDesc) {
  let coeff = coeffDesc.map(toComplex).slice();
  let n = coeff.length - 1;
  while (n > 0 && cAbs2(coeff[0]) < 1e-30) {
    coeff = coeff.slice(1);
    n -= 1;
  }
  if (n <= 0) {
    return [];
  }
  if (n === 1) {
    return [cDiv(cScale(coeff[1], -1), coeff[0])];
  }

  const aLead = coeff[0];
  const norm = coeff.map((c) => cDiv(c, aLead));

  let R = 1;
  for (let i = 1; i < norm.length; i++) {
    const ri = cAbs(norm[i]);
    if (ri > 0) {
      const deg = n - i;
      if (deg > 0) {
        const radius = Math.pow(ri, 1 / deg);
        if (radius > R) R = radius;
      }
    }
  }
  R = 1.4 * (R + 1);

  const roots = new Array(n);
  for (let i = 0; i < n; i++) {
    const theta = 2 * Math.PI * (i + 0.5) / n;
    roots[i] = complex(R * Math.cos(theta), R * Math.sin(theta));
  }

  const maxIter = 260;
  const tol = 1e-14;

  function jIndex(i0) {
    return (i0 + 1) % n;
  }

  for (let it = 0; it < maxIter; it++) {
    let maxChange = 0;
    const next = new Array(n);
    for (let i = 0; i < n; i++) {
      const zi = roots[i];
      const pVal = polyEval(norm, zi);
      let denom = complex(1, 0);
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        denom = cMul(denom, cSub(zi, roots[j]));
      }
      let denom2 = denom;
      const tiny = 1e-16;
      if (cAbs2(denom2) < tiny * tiny) {
        denom2 = cAdd(denom2, complex(1e-12 * (i + 1), 1e-12 * (jIndex(i) + 1)));
      }
      const delta = cDiv(pVal, denom2);
      const newZi = cSub(zi, delta);
      next[i] = newZi;
      const ch = cAbs(cSub(newZi, zi));
      if (ch > maxChange) maxChange = ch;
    }
    for (let i = 0; i < n; i++) roots[i] = next[i];
    if (maxChange < tol) break;
  }

  return roots.map(normalizeRoot);
}

function solveQuarticRoots(y) {
  const yc = toComplex(y);
  const coeff = [
    complex(1, 0),
    complex(-1, 0),
    cSub(complex(-1, 0), cAdd(cScale(yc, 2), 1)),
    complex(1, 0),
    cMul(yc, cAdd(yc, 1)),
  ];
  return solvePolynomial(coeff);
}

function solvePolynomialCubicCoeffs(coeffDesc) {
  return solvePolynomial(coeffDesc.map((v) => toComplex(v)));
}

function cubicDiscRoot() {
  let a = -2;
  let b = -0.8;
  const cVal = (t) => 256 * t * t * t + 411 * t * t + 165 * t + 32;
  let fa = cVal(a);
  let fb = cVal(b);
  if (fa * fb > 0) {
    a = -1.5;
    b = -1;
    fa = cVal(a);
    fb = cVal(b);
  }
  for (let k = 0; k < 90; k++) {
    const m = 0.5 * (a + b);
    const fm = cVal(m);
    if (fa * fm <= 0) {
      b = m;
      fb = fm;
    } else {
      a = m;
      fa = fm;
    }
  }
  return 0.5 * (a + b);
}

function sortByModulus(roots) {
  return roots.slice().sort((u, v) => cAbs(v) - cAbs(u));
}

function linearSpace(lo, hi, n) {
  if (n <= 1) return [lo];
  const arr = [];
  const step = (hi - lo) / (n - 1);
  for (let i = 0; i < n; i++) {
    arr.push(lo + i * step);
  }
  return arr;
}

function minDistPair(roots) {
  let best = { i: 0, j: 1, d2: cAbs2(cSub(roots[0], roots[1])) };
  for (let i = 0; i < roots.length; i++) {
    for (let j = i + 1; j < roots.length; j++) {
      const d2 = cAbs2(cSub(roots[i], roots[j]));
      if (d2 < best.d2) {
        best = { i, j, d2 };
      }
    }
  }
  return [best.i, best.j];
}

function zmCoeffs(m) {
  const coeffs = [ [1], [1, 1], [1, 2, 1], [1, 3, 3, 1] ];
  if (m <= 3) {
    return coeffs[m];
  }
  const c = (arr, k) => (k < 0 || k >= arr.length ? 0 : arr[k]);
  for (let t = 4; t <= m; t++) {
    const kMax = Math.floor((t + 3) / 2);
    const cur = new Array(kMax + 1).fill(0);
    const p1 = coeffs[t - 1];
    const p2 = coeffs[t - 2];
    const p3 = coeffs[t - 3];
    const p4 = coeffs[t - 4];
    for (let k = 0; k <= kMax; k++) {
      cur[k] = c(p1, k) + 2 * c(p2, k - 1) + c(p2, k)
        - c(p3, k)
        - c(p4, k - 1)
        - c(p4, k - 2);
    }
    coeffs.push(cur);
  }
  return coeffs[m];
}

function extractRootsFromYPolynomial(m) {
  const coeffAsc = zmCoeffs(m);
  const coeffDesc = coeffAsc.slice().reverse().map(toComplex);
  const roots = solvePolynomial(coeffDesc);
  return roots;
}

function writeTable(file, lines) {
  fs.writeFileSync(file, lines.join('\n') + '\n');
}

function collectContourSegments(xs, ys, values, target = 0) {
  const nx = xs.length;
  const ny = ys.length;
  const segs = [];

  const interp = (p1, p2, v1, v2) => {
    const dv = v1 - v2;
    const t = dv === 0 ? 0.5 : (target - v2) / dv;
    const tt = Math.min(1, Math.max(0, t));
    return {
      x: p1.x + (p2.x - p1.x) * tt,
      y: p1.y + (p2.y - p1.y) * tt,
    };
  };

  for (let j = 0; j < ny - 1; j++) {
    for (let i = 0; i < nx - 1; i++) {
      const v00 = values[j][i];
      const v10 = values[j][i + 1];
      const v11 = values[j + 1][i + 1];
      const v01 = values[j + 1][i];

      if (!isFinite(v00) || !isFinite(v10) || !isFinite(v11) || !isFinite(v01)) {
        continue;
      }

      const p00 = { x: xs[i], y: ys[j] };
      const p10 = { x: xs[i + 1], y: ys[j] };
      const p11 = { x: xs[i + 1], y: ys[j + 1] };
      const p01 = { x: xs[i], y: ys[j + 1] };

      const pts = [];
      const addIfCross = (va, vb, pa, pb) => {
        const da = va - target;
        const db = vb - target;
        if (Math.abs(da) < 1e-14 && Math.abs(db) < 1e-14) {
          return;
        }
        if (Math.abs(da) < 1e-14) {
          pts.push(pa);
        } else if (Math.abs(db) < 1e-14) {
          pts.push(pb);
        } else if (da * db < 0) {
          pts.push(interp(pa, pb, va, vb));
        }
      };

      addIfCross(v00, v10, p00, p10);
      addIfCross(v10, v11, p10, p11);
      addIfCross(v11, v01, p11, p01);
      addIfCross(v01, v00, p01, p00);

      if (pts.length === 2) {
        segs.push([pts[0], pts[1]]);
      } else if (pts.length === 4) {
        segs.push([pts[0], pts[2]], [pts[1], pts[3]]);
      }
    }
  }

  const lines = [];
  for (const seg of segs) {
    lines.push(`${seg[0].x} ${seg[0].y}`);
    lines.push(`${seg[1].x} ${seg[1].y}`);
    lines.push('');
  }
  return lines;
}

function writeAll() {
  ensureDir(DATA_DIR);

  const yLY = cubicDiscRoot();
  const summaryPath = path.join(DATA_DIR, 'fig_generation_summary.txt');
  const summary = [];

  // Figure 1: branch cubic c(y) on real axis.
  const yGrid1 = linearSpace(-2.5, 1, 1400);
  const fig1 = yGrid1.map((y) => `${y} ${256 * y * y * y + 411 * y * y + 165 * y + 32}`);
  writeTable(path.join(DATA_DIR, 'fig01_branch_cubic_values.dat'), fig1);

  // Figure 2: cubic roots in the complex y-plane.
  const cubicRoots = solvePolynomialCubicCoeffs([32, 165, 411, 256]);
  const fig2 = cubicRoots.map((z) => `${z.re} ${z.im}`);
  writeTable(path.join(DATA_DIR, 'fig02_branch_roots_complex.dat'), fig2);

  // Figure 3: log|lambda_i(y)| on real y.
  const fig3 = [];
  for (const y of linearSpace(-2.5, 2.2, 1600)) {
    const roots = sortByModulus(solveQuarticRoots(y));
    const l = roots.map((z) => Math.log(Math.max(cAbs(z), 1e-30)));
    while (l.length < 4) l.push(-30);
    fig3.push(`${y} ${l[0]} ${l[1]} ${l[2]} ${l[3]}`);
  }
  writeTable(path.join(DATA_DIR, 'fig03_root_moduli_real.dat'), fig3);

  // Figure 4: local collision pair around y_LY.
  const fig4 = [];
  for (const y of linearSpace(yLY - 0.02, yLY + 0.02, 1200)) {
    const roots = solveQuarticRoots(y);
    const [i, j] = minDistPair(roots);
    const r1 = roots[i];
    const r2 = roots[j];
    fig4.push(`${y} ${r1.re} ${r1.im} ${r2.re} ${r2.im}`);
  }
  writeTable(path.join(DATA_DIR, 'fig04_local_collision_zoom.dat'), fig4);

  // Figure 5: dominant/subdominant gaps on negative real axis.
  const fig5 = [];
  for (const y of linearSpace(-3, 0, 1400)) {
    const roots = sortByModulus(solveQuarticRoots(y));
    const m0 = cAbs(roots[0]);
    const m1 = cAbs(roots[1]);
    const m2 = cAbs(roots[2]);
    const dom = Math.log(Math.max(m0, 1e-30));
    const sub = Math.log(Math.max(m1, 1e-30));
    const gap12 = dom - sub;
    const gap23 = sub - Math.log(Math.max(m2, 1e-30));
    fig5.push(`${y} ${dom} ${sub} ${gap12} ${gap23}`);
  }
  writeTable(path.join(DATA_DIR, 'fig05_dominance_gap_real.dat'), fig5);

  // Figures 6--9: zero clouds for selected m.
  const mValues = [12, 20, 28, 36];
  for (let idx = 0; idx < mValues.length; idx++) {
    const m = mValues[idx];
    const roots = extractRootsFromYPolynomial(m).slice().sort((u, v) => u.re - v.re || u.im - v.im);
    const fig = roots.map((z) => `${z.re} ${z.im}`);
    writeTable(path.join(DATA_DIR, `fig0${6 + idx}_zero_cloud_m${m}.dat`), fig);
  }

  // Figures 10--12: equimodular contour data.
  // We track roots continuously across the sampled grid so that
  // branch labels are stable enough for meaningful contour traces.
  const xs = linearSpace(-3, 2.5, 140);
  const ys = linearSpace(-2.5, 2.5, 140);
  const d12 = Array.from({ length: ys.length }, () => Array(xs.length).fill(NaN));
  const d13 = Array.from({ length: ys.length }, () => Array(xs.length).fill(NaN));
  const d23 = Array.from({ length: ys.length }, () => Array(xs.length).fill(NaN));
  const d02 = Array.from({ length: ys.length }, () => Array(xs.length).fill(NaN));
  const d03 = Array.from({ length: ys.length }, () => Array(xs.length).fill(NaN));
  const scan = {
    d12: { min: Infinity, max: -Infinity },
    d13: { min: Infinity, max: -Infinity },
    d23: { min: Infinity, max: -Infinity },
    d02: { min: Infinity, max: -Infinity },
    d03: { min: Infinity, max: -Infinity },
  };
  let prevRow = null;
  const rootsGrid = Array.from({ length: ys.length }, () => new Array(xs.length));

  for (let j = 0; j < ys.length; j++) {
    let prev = null;
    for (let i = 0; i < xs.length; i++) {
      const y = complex(xs[i], ys[j]);
      const roots = solveQuarticRoots(y).slice().sort((u, v) => (u.re - v.re) || (u.im - v.im));
      let ordered;
      if (!prevRow || (i === 0 && !prevRow[i])) {
        ordered = sortBySeed(prev, roots);
      } else {
        ordered = sortBySeed(i === 0 ? prevRow[i] : prev, roots);
      }
      prev = ordered;
      rootsGrid[j][i] = ordered;
      if (roots.length < 3) continue;
      const m0 = Math.max(cAbs(ordered[0]), 1e-30);
      const m1 = Math.max(cAbs(ordered[1]), 1e-30);
      const m2 = Math.max(cAbs(ordered[2]), 1e-30);
      d12[j][i] = Math.log(m0) - Math.log(m1);
      d13[j][i] = Math.log(m0) - Math.log(m2);
      d23[j][i] = Math.log(m1) - Math.log(m2);
      const m3 = Math.max(cAbs(ordered[3]), 1e-30);
      d02[j][i] = Math.log(m0) - Math.log(m3);
      d03[j][i] = Math.log(m1) - Math.log(m3);
      scan.d12.min = Math.min(scan.d12.min, d12[j][i]);
      scan.d12.max = Math.max(scan.d12.max, d12[j][i]);
      scan.d13.min = Math.min(scan.d13.min, d13[j][i]);
      scan.d13.max = Math.max(scan.d13.max, d13[j][i]);
      scan.d23.min = Math.min(scan.d23.min, d23[j][i]);
      scan.d23.max = Math.max(scan.d23.max, d23[j][i]);
      scan.d02.min = Math.min(scan.d02.min, d02[j][i]);
      scan.d02.max = Math.max(scan.d02.max, d02[j][i]);
      scan.d03.min = Math.min(scan.d03.min, d03[j][i]);
      scan.d03.max = Math.max(scan.d03.max, d03[j][i]);
    }
    prevRow = rootsGrid[j];
  }

  writeTable(path.join(DATA_DIR, 'fig10_eq12_contour.dat'), collectContourSegments(xs, ys, d12, 0));
  writeTable(path.join(DATA_DIR, 'fig11_eq13_contour.dat'), collectContourSegments(xs, ys, d13, 0));
  writeTable(path.join(DATA_DIR, 'fig12_eq23_contour.dat'), collectContourSegments(xs, ys, d23, 0));
  summary.push(`y_LY\t${yLY}`);
  summary.push(`roots_cubic\t${cubicRoots.map((z) => `(${z.re},${z.im})`).join('; ')}`);
  summary.push(`scan_d12\t${scan.d12.min}\t${scan.d12.max}`);
  summary.push(`scan_d13\t${scan.d13.min}\t${scan.d13.max}`);
  summary.push(`scan_d23\t${scan.d23.min}\t${scan.d23.max}`);
  summary.push(`scan_d02\t${scan.d02.min}\t${scan.d02.max}`);
  summary.push(`scan_d03\t${scan.d03.min}\t${scan.d03.max}`);
  writeTable(summaryPath, summary);
}

writeAll();
