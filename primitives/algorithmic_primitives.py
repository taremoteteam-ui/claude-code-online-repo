"""Working algorithmic primitives: the reusable kernels that coding-problem
solutions are decomposed INTO.

The coding-agent lane (scripts/seeds/universal_families_coding_agent_seed.py)
DESCRIBES the classic algorithm patterns as catalog cards. This module is the
layer beneath: real, correct, stdlib-only IMPLEMENTATIONS of those patterns, each
one a primitive that multiple problem solutions reuse. Solving a new problem is
then a matter of composing these - which is the whole point of a primitive atlas:
problem #N reuses kernels mined from problems #1..N-1.

Each kernel is pure (no I/O, effect == none). PRIMITIVES maps a stable id to its
function, the recurring pattern it embodies, and its typed ports (CamelCase so
they parse on the capability graph). SELF_TESTS maps each id to a
(kwargs, expected) fixture the checker runs so a kernel that does not actually
work goes red. candidate=true / serves_truth=false.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque


# --- kernels ---------------------------------------------------------------

def two_pointer_pair_sum(nums: list[int], target: int) -> list[int]:
    """Indices of the two numbers summing to target (hash pass). [] if none."""
    seen: dict[int, int] = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return [seen[target - x], i]
        seen[x] = i
    return []


def sliding_window_longest_unique(s: str) -> int:
    """Length of the longest substring with no repeated character."""
    last: dict[str, int] = {}
    start = best = 0
    for i, c in enumerate(s):
        if c in last and last[c] >= start:
            start = last[c] + 1
        last[c] = i
        best = max(best, i - start + 1)
    return best


def binary_search_answer(lo: int, hi: int, feasible) -> int:
    """Least value in [lo, hi] for which the monotone predicate feasible() holds.
    Binary search on the answer. Assumes feasible is False..False,True..True."""
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def prefix_sums(nums: list[int]) -> list[int]:
    """prefix[i] = sum(nums[:i]); len == len(nums)+1."""
    out = [0]
    for x in nums:
        out.append(out[-1] + x)
    return out


def counting_frequency(items: list) -> dict:
    """Hashmap multiset count of items."""
    return dict(Counter(items))


class UnionFind:
    """Disjoint-set union with path compression + union by size."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.components -= 1
        return True


def union_find_components(n: int, edges: list[list[int]]) -> int:
    """Number of connected components over n nodes given undirected edges."""
    uf = UnionFind(n)
    for a, b in edges:
        uf.union(a, b)
    return uf.components


def bfs_shortest_path(graph: dict, src, dst) -> int:
    """Fewest edges from src to dst in an unweighted adjacency-dict graph.
    -1 if unreachable, 0 if src == dst."""
    if src == dst:
        return 0
    seen = {src}
    q = deque([(src, 0)])
    while q:
        node, d = q.popleft()
        for nxt in graph.get(node, []):
            if nxt == dst:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return -1


def dfs_reachable(graph: dict, src) -> set:
    """Set of nodes reachable from src (including src) via DFS."""
    seen = set()
    stack = [src]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, []))
    return seen


def monotonic_stack_next_greater(nums: list[int]) -> list[int]:
    """For each element, the next strictly greater element to its right (-1 if
    none), via a decreasing monotonic stack."""
    res = [-1] * len(nums)
    stack: list[int] = []   # indices, values decreasing
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] < x:
            res[stack.pop()] = x
        stack.append(i)
    return res


def kadane_max_subarray(nums: list[int]) -> int:
    """Maximum sum of a non-empty contiguous subarray (Kadane's DP)."""
    best = cur = nums[0]
    for x in nums[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


def topological_order(n: int, edges: list[list[int]]) -> list[int]:
    """A topological order of nodes 0..n-1 given directed edges [u,v] (u before
    v). Returns [] if the graph has a cycle (Kahn's algorithm)."""
    adj = defaultdict(list)
    indeg = [0] * n
    for u, v in edges:
        adj[u].append(v)
        indeg[v] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return order if len(order) == n else []


def dp_coin_change(coins: list[int], amount: int) -> int:
    """Fewest coins summing to amount, -1 if impossible (unbounded-knapsack DP)."""
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return dp[amount] if dp[amount] != INF else -1


# --- registry + self-test fixtures -----------------------------------------

def _pattern(pid, fn, does, in_edge, out_edge, pattern):
    return {"primitive_id": pid, "fn": fn, "does": does,
            "input_edge": in_edge, "output_edge": out_edge, "pattern": pattern}


PRIMITIVES = {
    "algo:two_pointer_pair_sum": _pattern(
        "algo:two_pointer_pair_sum", two_pointer_pair_sum,
        "find two indices summing to a target", "IntArray+IntTarget", "IndexPair", "two_pointers"),
    "algo:sliding_window_longest_unique": _pattern(
        "algo:sliding_window_longest_unique", sliding_window_longest_unique,
        "longest substring without repeats", "TextString", "IntLength", "sliding_window"),
    "algo:binary_search_answer": _pattern(
        "algo:binary_search_answer", binary_search_answer,
        "least feasible value under a monotone predicate", "SearchBounds+Predicate", "IntAnswer",
        "binary_search"),
    "algo:prefix_sums": _pattern(
        "algo:prefix_sums", prefix_sums, "prefix-sum array", "IntArray", "PrefixArray", "prefix_sum"),
    "algo:counting_frequency": _pattern(
        "algo:counting_frequency", counting_frequency, "multiset frequency map",
        "ItemList", "FrequencyMap", "hashing"),
    "algo:union_find_components": _pattern(
        "algo:union_find_components", union_find_components,
        "count connected components", "NodeCount+EdgeList", "ComponentCount", "union_find"),
    "algo:bfs_shortest_path": _pattern(
        "algo:bfs_shortest_path", bfs_shortest_path,
        "fewest edges between two nodes", "AdjacencyGraph+NodePair", "IntDistance", "bfs"),
    "algo:dfs_reachable": _pattern(
        "algo:dfs_reachable", dfs_reachable, "nodes reachable from a source",
        "AdjacencyGraph+NodeId", "NodeSet", "dfs"),
    "algo:monotonic_stack_next_greater": _pattern(
        "algo:monotonic_stack_next_greater", monotonic_stack_next_greater,
        "next greater element to the right", "IntArray", "NextGreaterArray", "monotonic_stack"),
    "algo:kadane_max_subarray": _pattern(
        "algo:kadane_max_subarray", kadane_max_subarray, "maximum contiguous subarray sum",
        "IntArray", "IntMaxSum", "dynamic_programming"),
    "algo:topological_order": _pattern(
        "algo:topological_order", topological_order, "topological order or empty on cycle",
        "NodeCount+DirectedEdgeList", "NodeOrder", "topological_sort"),
    "algo:dp_coin_change": _pattern(
        "algo:dp_coin_change", dp_coin_change, "fewest coins for an amount",
        "CoinSet+IntTarget", "IntCoinCount", "dynamic_programming"),
}

SELF_TESTS = {
    "algo:two_pointer_pair_sum": ({"nums": [2, 7, 11, 15], "target": 9}, [0, 1]),
    "algo:sliding_window_longest_unique": ({"s": "abcabcbb"}, 3),
    "algo:binary_search_answer": ({"lo": 0, "hi": 10, "feasible": (lambda m: m * m >= 17)}, 5),
    "algo:prefix_sums": ({"nums": [1, 2, 3]}, [0, 1, 3, 6]),
    "algo:counting_frequency": ({"items": ["a", "b", "a"]}, {"a": 2, "b": 1}),
    "algo:union_find_components": ({"n": 5, "edges": [[0, 1], [1, 2], [3, 4]]}, 2),
    "algo:bfs_shortest_path": ({"graph": {0: [1, 2], 1: [3], 2: [3], 3: []}, "src": 0, "dst": 3}, 2),
    "algo:dfs_reachable": ({"graph": {0: [1], 1: [2], 2: [], 3: []}, "src": 0}, {0, 1, 2}),
    "algo:monotonic_stack_next_greater": ({"nums": [2, 1, 2, 4, 3]}, [4, 2, 4, -1, -1]),
    "algo:kadane_max_subarray": ({"nums": [-2, 1, -3, 4, -1, 2, 1, -5, 4]}, 6),
    "algo:topological_order": ({"n": 3, "edges": [[0, 1], [1, 2]]}, [0, 1, 2]),
    "algo:dp_coin_change": ({"coins": [1, 2, 5], "amount": 11}, 3),
}


def run_self_test(pid: str) -> bool:
    """Run one kernel's fixture and check the result. Deterministic."""
    kwargs, expected = SELF_TESTS[pid]
    return PRIMITIVES[pid]["fn"](**kwargs) == expected
