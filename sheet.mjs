// node sheet.mjs index.html --ticks 1,120,300 [--scale 6] [--crop x,y,w,h] [--out sheet.png] [--at 10:floor,400:bed]
// Runs the page's <script id="core"> headlessly and writes a contact sheet of the chosen ticks.
import fs from 'fs';
import zlib from 'zlib';
import vm from 'vm';

const [file, ...rest] = process.argv.slice(2);
const opt = {};
for (let i = 0; i < rest.length; i += 2) opt[rest[i].replace(/^--/, '')] = rest[i + 1];

const html = fs.readFileSync(file, 'utf8');
const core = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
// hand-typed rule: blit() is the only thing allowed to write a pixel, and nothing may compute shapes
const writes = core.match(/\bT\[[^\]]+\]\s*=[^=]/g) || [];
const banned = core.match(/Math\.(random|sin|cos|atan2|hypot|sqrt)|\.fill\(|\.set\(/g) || [];
if (writes.length !== 1 || banned.length) {
  console.error('not hand-typed: ' + writes.length + ' pixel writes (want 1, inside blit), banned calls: ' + (banned.join(', ') || 'none'));
  process.exit(1);
}
const ctx = { Math, Uint8Array, Int8Array, Int16Array, Float32Array, Error };
vm.createContext(ctx);
vm.runInContext(core + '\nthis.SCENE = SCENE;', ctx);
const S = ctx.SCENE;

const ticks = (opt.ticks || '1').split(',').map(Number);
const scale = +(opt.scale || 4);
const [cx, cy, cw, ch] = opt.crop ? opt.crop.split(',').map(Number) : [0, 0, S.W, S.H];
const pal = S.PAL.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
const gap = 4, cols = +(opt.cols || ticks.length), rows = Math.ceil(ticks.length / cols);
const OW = cols * cw * scale + (cols + 1) * gap, OH = rows * ch * scale + (rows + 1) * gap;
const rgb = Buffer.alloc(OW * OH * 3, 48);

let t = 0;
const labels = [];
const at = new Map((opt.at || '').split(',').filter(Boolean).map(p => { const [k, v] = p.split(':'); return [+k, v]; }));
ticks.forEach((tk, n) => {
  while (t < tk) { if (at.has(t)) S.go(at.get(t)); S.update(); t++; }
  S.draw();
  labels.push(tk + ':' + S.state());
  const ox = gap + (n % cols) * (cw * scale + gap), oy = gap + ((n / cols) | 0) * (ch * scale + gap);
  for (let y = 0; y < ch * scale; y++) for (let x = 0; x < cw * scale; x++) {
    const c = pal[S.fb[(cy + ((y / scale) | 0)) * S.W + cx + ((x / scale) | 0)]];
    const o = ((oy + y) * OW + ox + x) * 3;
    rgb[o] = c[0]; rgb[o + 1] = c[1]; rgb[o + 2] = c[2];
  }
});

const CRC = new Int32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c; });
const crc32 = buf => { let c = -1; for (const b of buf) c = CRC[(c ^ b) & 0xff] ^ (c >>> 8); return (c ^ -1) >>> 0; };
const chunk = (type, data) => {
  const td = Buffer.concat([Buffer.from(type), data]);
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
};
const raw = Buffer.alloc((OW * 3 + 1) * OH);
for (let y = 0; y < OH; y++) rgb.copy(raw, y * (OW * 3 + 1) + 1, y * OW * 3, (y + 1) * OW * 3);
const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(OW, 0); ihdr.writeUInt32BE(OH, 4); ihdr[8] = 8; ihdr[9] = 2;
const out = opt.out || 'sheet.png';
fs.writeFileSync(out, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]));
console.log(out, OW + 'x' + OH, labels.join(' | '));
