// growth.cpp - fast exact counting for Shuffledot-style tile sets (used by ../fast_count.py)
//
// Bars are straight 1 x L runs of grid squares.  Two quantities are computed:
//
//   G   Number of ordered "growth sequences" of K bars: the first bar is vertical at a fixed
//       spot, and every later bar must not overlap and must touch (along an edge) at least
//       one bar already placed.  Which tile goes in which bar is handled in Python.
//   S   For the two mirror symmetries that keep the first bar in place, the growth sequences
//       that are unchanged by the mirror, summarised by a bitmask of which positions in the
//       sequence hold a bar that must carry a palindromic tile.
//   F   Number of connected sets of K bars, counted up to translation only (Redelmeier's
//       algorithm).  Used for counting final layouts.
//
// Build:  g++ -O2 -o growth growth.cpp
// Run:    ./growth L K          prints lines "G <n>", "S0 <mask> <count>", "S1 ...", "F <n>"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <vector>
using namespace std;

static const int N = 128, OFF = 56;          // grid size and where the first bar sits
static int L, K;
static int occ[N * N];
static int stampArr[N * N * 2], curStamp = 0;
struct Bar { int x, y, o; };                 // o = 0 horizontal, 1 vertical; (x,y) = top-left cell
static inline int cellIdx(int x, int y) { return y * N + x; }
static inline int barId(const Bar& b) { return cellIdx(b.x, b.y) * 2 + b.o; }
static inline bool isFree(const Bar& b) {
    for (int j = 0; j < L; j++)
        if (occ[cellIdx(b.x + (b.o == 0 ? j : 0), b.y + (b.o == 1 ? j : 0))]) return false;
    return true;
}
static inline void put(const Bar& b, int v) {
    for (int j = 0; j < L; j++) occ[cellIdx(b.x + (b.o == 0 ? j : 0), b.y + (b.o == 1 ? j : 0))] += v;
}

// ---------------------------------------------------------------- growth sequences
static vector<Bar> placed;
template <class F> static void candidates(vector<Bar>& out, F allowed) {
    out.clear();
    ++curStamp;
    static const int dx[4] = {1, -1, 0, 0}, dy[4] = {0, 0, 1, -1};
    for (const Bar& p : placed)
        for (int j = 0; j < L; j++) {
            int cx = p.x + (p.o == 0 ? j : 0), cy = p.y + (p.o == 1 ? j : 0);
            for (int d = 0; d < 4; d++) {
                int nx = cx + dx[d], ny = cy + dy[d];
                if (occ[cellIdx(nx, ny)]) continue;
                for (int o = 0; o < 2; o++)
                    for (int t = 0; t < L; t++) {
                        Bar b{nx - (o == 0 ? t : 0), ny - (o == 1 ? t : 0), o};
                        int id = barId(b);
                        if (stampArr[id] == curStamp) continue;
                        stampArr[id] = curStamp;
                        if (isFree(b) && allowed(b)) out.push_back(b);
                    }
            }
        }
}
static long long G = 0;
static void growAll() {
    vector<Bar> c;
    candidates(c, [](const Bar&) { return true; });
    if ((int)placed.size() == K - 1) { G += (long long)c.size(); return; }   // just count the last step
    for (const Bar& b : c) { put(b, 1); placed.push_back(b); growAll(); placed.pop_back(); put(b, -1); }
}
static map<long long, long long> masks;
// mode 0: mirror x -> -x (axis through the first bar).  mode 1: mirror about the first bar's mid-row.
static void growSymmetric(int mode, long long mask) {
    if ((int)placed.size() == K) { masks[mask]++; return; }
    auto allowed = [&](const Bar& b) {
        if (mode == 0) return b.o == 1 ? b.x == OFF : (L % 2 == 1 && b.x == OFF - (L - 1) / 2);
        return b.o == 0 ? (L % 2 == 1 && b.y == OFF + (L - 1) / 2) : b.y == OFF;
    };
    vector<Bar> c;
    candidates(c, allowed);
    for (const Bar& b : c) {
        bool needsPalindrome = (mode == 0) ? (b.o == 0) : (b.o == 1);   // the mirror reverses such a bar
        long long m = mask | (needsPalindrome ? (1LL << placed.size()) : 0LL);
        put(b, 1); placed.push_back(b); growSymmetric(mode, m); placed.pop_back(); put(b, -1);
    }
}

// ---------------------------------------------------------------- Redelmeier: connected sets of bars
static long long F = 0;
static char seen[N * N * 2];
static int rootId;
static void redelmeier(vector<Bar> untried, int size) {
    while (!untried.empty()) {
        Bar v = untried.back(); untried.pop_back();
        if (!isFree(v)) continue;
        put(v, 1);
        if (size + 1 == K) F++;
        else {
            vector<Bar> next = untried;
            static const int dx[4] = {1, -1, 0, 0}, dy[4] = {0, 0, 1, -1};
            vector<int> marks;
            for (int j = 0; j < L; j++) {
                int cx = v.x + (v.o == 0 ? j : 0), cy = v.y + (v.o == 1 ? j : 0);
                for (int d = 0; d < 4; d++) {
                    int nx = cx + dx[d], ny = cy + dy[d];
                    if (occ[cellIdx(nx, ny)]) continue;
                    for (int o = 0; o < 2; o++)
                        for (int t = 0; t < L; t++) {
                            Bar b{nx - (o == 0 ? t : 0), ny - (o == 1 ? t : 0), o};
                            int id = barId(b);
                            if (id <= rootId || seen[id] || !isFree(b)) continue;
                            seen[id] = 1; marks.push_back(id); next.push_back(b);
                        }
                }
            }
            redelmeier(next, size + 1);
            for (int id : marks) seen[id] = 0;
        }
        put(v, -1);
    }
}

int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s L K\n", argv[0]); return 1; }
    L = atoi(argv[1]); K = atoi(argv[2]);
    if (L < 1 || K < 1 || K * L + 2 >= OFF) { fprintf(stderr, "L*K too large for this build\n"); return 1; }
    // growth sequences (first bar vertical at the origin)
    Bar first{OFF, OFF, 1};
    put(first, 1); placed.push_back(first);
    growAll();
    printf("G %lld\n", G);
    for (int mode = 0; mode < 2; mode++) {
        masks.clear();
        growSymmetric(mode, mode == 1 ? 1LL : 0LL);   // in mode 1 the first bar is itself reversed by the mirror
        for (auto& kv : masks) printf("S%d %lld %lld\n", mode, kv.first, kv.second);
    }
    placed.clear(); put(first, -1);
    // connected sets, up to translation
    for (int o = 0; o < 2; o++) {
        memset(seen, 0, sizeof seen); memset(occ, 0, sizeof occ);
        Bar root{OFF, OFF, o};
        rootId = barId(root); seen[rootId] = 1;
        redelmeier(vector<Bar>{root}, 0);
    }
    printf("F %lld\n", F);
    return 0;
}
