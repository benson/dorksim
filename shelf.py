# The dark wood shelf under the room that the bone buttons sit on: 480x26, explicit plank spec.
# chars: O dark wood, P wood, Q light edge
W, H = 480, 26
GRAIN = [(5, 12, 40), (8, 70, 34), (11, 130, 52), (14, 200, 28), (17, 250, 46), (7, 310, 38),
         (12, 372, 44), (19, 420, 36), (21, 30, 30), (15, 150, 22), (9, 450, 24), (20, 330, 40)]
JOINTS = [96, 241, 388]
rows = []
for y in range(H):
    row = ['O' if y in (0, H - 1, H - 2) else 'Q' if y == 1 else 'P'] * W
    for gy, gx, gl in GRAIN:
        if gy == y:
            for x in range(gx, min(W, gx + gl)): row[x] = 'O'
    if 2 <= y < H - 2:
        for j in JOINTS: row[j] = 'O'; row[j + 1] = 'Q'
    rows.append(''.join(row))
open('art/shelf.txt', 'w').write('\n'.join(rows) + '\n')
print(len(rows), set(len(r) for r in rows))
