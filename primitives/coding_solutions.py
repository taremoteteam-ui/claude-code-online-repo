"""Working solutions to coding problems, each COMPOSED FROM algorithmic
primitives.

This is the "actually build the solution" half of the coding-problem lane: every
function here solves one problem in fixtures/coding-problems/problems.json, and it
does so by calling kernels from primitives/algorithmic_primitives.py rather than
re-deriving the algorithm. SOLUTIONS records, per problem, the function and the
primitive ids it composes - which is exactly the decomposition the atlas stores,
and what lets us MEASURE reuse (few kernels covering many problems).

The checker (scripts/check_coding_primitive_pack.py) runs every solution against
that problem's test cases, so a solution that does not actually solve goes red.
Pure/deterministic; stdlib only; candidate=true / serves_truth=false.
"""

from __future__ import annotations

from primitives.algorithmic_primitives import (bfs_shortest_path,
                                               binary_search_answer,
                                               counting_frequency,
                                               dfs_reachable, dp_coin_change,
                                               kadane_max_subarray,
                                               monotonic_stack_next_greater,
                                               prefix_sums,
                                               sliding_window_longest_unique,
                                               topological_order,
                                               two_pointer_pair_sum,
                                               union_find_components)


def two_sum(nums, target):
    return two_pointer_pair_sum(nums, target)


def longest_unique_substring(s):
    return sliding_window_longest_unique(s)


def group_anagrams(words):
    groups: dict = {}
    for w in words:
        key = tuple(sorted(counting_frequency(list(w)).items()))
        groups.setdefault(key, []).append(w)
    return sorted(sorted(g) for g in groups.values())


def valid_anagram(s, t):
    return counting_frequency(list(s)) == counting_frequency(list(t))


def ransom_note(note, magazine):
    have = counting_frequency(list(magazine))
    need = counting_frequency(list(note))
    return all(have.get(c, 0) >= k for c, k in need.items())


def number_of_islands(grid):
    if not grid or not grid[0]:
        return 0
    rows, cols = len(grid), len(grid[0])
    idx = {}
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                idx[(r, c)] = len(idx)
    edges = []
    for (r, c), i in idx.items():
        for dr, dc in ((1, 0), (0, 1)):
            nb = (r + dr, c + dc)
            if nb in idx:
                edges.append([i, idx[nb]])
    return union_find_components(len(idx), edges)


def number_of_provinces(is_connected):
    n = len(is_connected)
    edges = [[i, j] for i in range(n) for j in range(i + 1, n) if is_connected[i][j] == 1]
    return union_find_components(n, edges)


def course_schedule(num_courses, prerequisites):
    edges = [[b, a] for a, b in prerequisites]   # b must come before a
    return len(topological_order(num_courses, edges)) == num_courses


def course_order(num_courses, prerequisites):
    edges = [[b, a] for a, b in prerequisites]
    return topological_order(num_courses, edges)


def maximum_subarray(nums):
    return kadane_max_subarray(nums)


def next_greater_element(nums):
    return monotonic_stack_next_greater(nums)


def coin_change(coins, amount):
    return dp_coin_change(coins, amount)


def subarray_sum_equals_k(nums, k):
    pref = prefix_sums(nums)
    seen: dict = {}
    ans = 0
    for p in pref:
        ans += seen.get(p - k, 0)
        seen[p] = seen.get(p, 0) + 1
    return ans


def koko_eating_bananas(piles, h):
    def feasible(speed):
        return sum(-(-p // speed) for p in piles) <= h
    return binary_search_answer(1, max(piles), feasible)


def min_ship_capacity(weights, days):
    def feasible(cap):
        need, cur = 1, 0
        for w in weights:
            if cur + w > cap:
                need += 1
                cur = 0
            cur += w
        return need <= days
    return binary_search_answer(max(weights), sum(weights), feasible)


def _one_letter_apart(a, b):
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def word_ladder_length(begin, end, word_list):
    nodes = set(word_list) | {begin}
    if end not in nodes:
        return 0
    graph = {w: [u for u in nodes if _one_letter_apart(w, u)] for w in nodes}
    dist = bfs_shortest_path(graph, begin, end)
    return dist + 1 if dist >= 0 else 0   # number of words in the shortest chain


def path_exists(n, edges, src, dst):
    graph: dict = {i: [] for i in range(n)}
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    return dst in dfs_reachable(graph, src)


# problem_id -> {fn, uses}. `uses` is the decomposition the checker cross-checks
# against the problem fixture's primitive_uses.
SOLUTIONS = {
    "two_sum": {"fn": two_sum, "uses": ["algo:two_pointer_pair_sum"]},
    "longest_unique_substring": {"fn": longest_unique_substring,
                                 "uses": ["algo:sliding_window_longest_unique"]},
    "group_anagrams": {"fn": group_anagrams, "uses": ["algo:counting_frequency"]},
    "valid_anagram": {"fn": valid_anagram, "uses": ["algo:counting_frequency"]},
    "ransom_note": {"fn": ransom_note, "uses": ["algo:counting_frequency"]},
    "number_of_islands": {"fn": number_of_islands, "uses": ["algo:union_find_components"]},
    "number_of_provinces": {"fn": number_of_provinces, "uses": ["algo:union_find_components"]},
    "course_schedule": {"fn": course_schedule, "uses": ["algo:topological_order"]},
    "course_order": {"fn": course_order, "uses": ["algo:topological_order"]},
    "maximum_subarray": {"fn": maximum_subarray, "uses": ["algo:kadane_max_subarray"]},
    "next_greater_element": {"fn": next_greater_element, "uses": ["algo:monotonic_stack_next_greater"]},
    "coin_change": {"fn": coin_change, "uses": ["algo:dp_coin_change"]},
    "subarray_sum_equals_k": {"fn": subarray_sum_equals_k,
                              "uses": ["algo:prefix_sums", "algo:counting_frequency"]},
    "koko_eating_bananas": {"fn": koko_eating_bananas, "uses": ["algo:binary_search_answer"]},
    "min_ship_capacity": {"fn": min_ship_capacity, "uses": ["algo:binary_search_answer"]},
    "word_ladder_length": {"fn": word_ladder_length, "uses": ["algo:bfs_shortest_path"]},
    "path_exists": {"fn": path_exists, "uses": ["algo:dfs_reachable"]},
}
