# python build.py -> index.html
# Assembles the game from index.src.html and art/: the translated room, poses and bed, plus the shelf (shelf.py).
# Pose grids come from ../pixel-scenes/dork-guilty (translate2.py output, then hand cleanup).
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, 'art')

def rows_of(name):
    return [l.rstrip('\n') for l in open(os.path.join(ART, name + '.txt')) if l.strip()]

def content_box(rows):
    ys = [y for y, r in enumerate(rows) if r.strip('.')]
    xs = [x for r in rows for x, c in enumerate(r) if c != '.']
    return min(xs), max(xs), min(ys), max(ys)

# spot = where his feet/rump anchor lands in the room; torso = row repeated/dropped for breathing;
# eyes = top-left of each 8x8 eye patch (sprite-local); breath = ticks per breath half
POSES = {
    'sad':         dict(art='sad',         spot=(214, 262), torso=88, breath=48, eyes=[23, 18, 35, 46]),
    'floor':       dict(art='stand',       spot=(250, 212), torso=60, breath=48, eyes=[]),
    'sitcorner':   dict(art='sitcorner',   spot=(104, 130), torso=80, breath=48, eyes=[]),
    'standcorner': dict(art='standcorner', spot=(102, 134), torso=70, breath=48, eyes=[]),
    'bed':         dict(art='bed_dork',    spot=(0, 0),     torso=38, breath=80, eyes=[]),
}
CONF = json.load(open(os.path.join(ART, 'conf.json'))) if os.path.exists(os.path.join(ART, 'conf.json')) else {}
for k, v in CONF.get('poses', {}).items(): POSES[k].update({kk: tuple(vv) if kk == 'spot' else vv for kk, vv in v.items()})

def breathe_masked(rows, x0, x1, torso, chars):
    # inhale for a sprite inside a prop: in columns x0..x1, the run of dog pixels ending at the torso row
    # moves up one pixel (the torso pixel repeats), so only his back rises and the bed stays put
    g = [list(r) for r in rows]
    for x in range(x0, x1 + 1):
        if rows[torso][x] not in chars: continue
        y = torso
        while y - 1 >= 0 and rows[y - 1][x] in chars: y -= 1
        for yy in range(y, torso + 1):
            if yy - 1 >= 0: g[yy - 1][x] = rows[yy][x]
    return [''.join(r) for r in g]

def contact_shadow(rows, reach=0.22):
    # shadow drawn under the sprite, built from its own outline: the floor line is the lower convex hull
    # of the lowest pixels (feet, rump); every floor pixel between the body's underside and that line is
    # shaded in a band hugging that line (light 'q'), and the 2 rows right under each contact are dark ('p')
    H, W = len(rows), len(rows[0])
    low = [max((y for y in range(H) if rows[y][x] != '.'), default=-1) for x in range(W)]
    top_band = H - 1 - int(H * reach)            # only the bottom part of the sprite can touch the floor
    pts = [(x, low[x]) for x in range(W) if low[x] >= top_band]
    hull = []
    for pt in pts:                                # lower hull, left to right (y grows downward)
        while len(hull) >= 2 and (hull[-1][0] - hull[-2][0]) * (pt[1] - hull[-2][1]) - (hull[-1][1] - hull[-2][1]) * (pt[0] - hull[-2][0]) >= 0:
            hull.pop()
        hull.append(pt)
    def floor_at(x):
        for (ax, ay), (bx, by) in zip(hull, hull[1:]):
            if ax <= x <= bx: return ay + (by - ay) * (x - ax) / max(1, bx - ax)
        return None
    out = [['.'] * W for _ in range(H + 3)]
    for x in range(W):
        f = floor_at(x)
        if f is None or low[x] < 0: continue
        f = round(f)
        for y in range(max(low[x] + 1, top_band, f - 4), min(H + 3, f + 3)):
            if y < H and rows[y][x] != '.': continue
            near = y <= low[x] + 2 and low[x] >= f - 3
            out[y][x] = 'p' if near else 'q'
    return [''.join(r) for r in out]

out = []
out.append('  var POSES = {')
spots = []
for name, p in POSES.items():
    rows = rows_of(p['art'])
    x0, x1, y0, y1 = content_box(rows)
    anchor = p.get('anchor') or [(x0 + x1) // 2, y1]
    body = ',\n'.join("      '%s'" % r for r in rows)
    extra = ''
    if p.get('mask'):
        mx0, mx1 = p['mask']
        inh = breathe_masked(rows, mx0, mx1, p['torso'], 'k0123456789DEFwab')
        extra = ' inhaleRows: [\n%s\n    ],' % ',\n'.join("      '%s'" % r for r in inh)
    out.append("    %s: { anchor: [%d, %d], torso: %d, breath: %d, small: %s, sdy: %d, at: %s, eyes: %s, rows: [\n%s\n    ] }," % (
        name, anchor[0], anchor[1], p['torso'], p['breath'], 'true' if p.get('small') else 'false',
        p.get('sdy', -2), json.dumps(p.get('at')), json.dumps(p['eyes']), body))
    if extra: out[-1] = out[-1].replace(' rows: [', extra + ' rows: [', 1)
    if not p.get('mask'):
        sh = contact_shadow(rows)
        out[-1] = out[-1].replace(' rows: [', ' shadow: [\n%s\n    ], rows: [' % ',\n'.join("      '%s'" % r for r in sh), 1)
    spots.append("%s: [%d, %d]" % (name, p['spot'][0], p['spot'][1]))
out[-1] = out[-1].rstrip(',')
out.append('  };')
bed = CONF.get('bed', {})
out.append('  var BED_POS = %s, BED_FRONT_OFF = %s;' % (json.dumps(bed.get('pos', [330, 150])), json.dumps(bed.get('front_off', [0, 0]))))
out.append('  var SPOTS = { %s };' % ', '.join(spots))
walk = [rows_of('walk1'), rows_of('walk2')]
wx0, wx1, wy0, wy1 = content_box(walk[0])
out.append('  var WALK_SDY = %d;' % CONF.get('walk_sdy', -2))
out.append('  var WALK_ANCHOR = %s;' % json.dumps(CONF.get('walk_anchor', [(wx0 + wx1) // 2, wy1])))
out.append('  var WALK_ROWS = [[\n%s\n  ], [\n%s\n  ]];' % tuple(',\n'.join("    '%s'" % r for r in w) for w in walk))
out.append('  var WALK_SHADOW_ROWS = [[\n%s\n  ], [\n%s\n  ]];' % tuple(',\n'.join("    '%s'" % r for r in contact_shadow(w)) for w in walk))
out.append('  var BED_ROWS = [\n%s\n  ];' % ',\n'.join("    '%s'" % r for r in rows_of('bed')))

src = open(os.path.join(HERE, 'index.src.html'), encoding='utf8').read()
room = ',\n'.join("    '%s'" % r for r in rows_of('room'))
out.append('  var SHELF_ROWS = [\n%s\n  ];' % ',\n'.join("    '%s'" % r for r in rows_of('shelf')))
def palette_js(name):
    return ''.join(",\n    '%s': '%s'" % tuple(l.split()) for l in open(os.path.join(ART, name)) if l.strip())
html = (src.replace('/*ROOM*/', room).replace('/*SPRITES*/', '\n'.join(out))
        .replace('/*BEDPAL*/', palette_js('bed.pal')).replace('/*ROOMPAL*/', palette_js('room.pal')))
open(os.path.join(HERE, 'index.html'), 'w', encoding='utf8', newline='\n').write(html)
print('index.html', len(html) // 1024, 'KB')
