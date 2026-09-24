"""共窑排程核心算法：位掩码动态规划。

器物数量 1～14 件：
1. 枚举全部子集 (2^n)，判断每个子集能否装入同一窑
   （总体积不超容量，且各器物允许烧成温度区间存在公共交集）；
2. dp[mask] = 覆盖 mask 中全部器物所需的最少窑次，枚举子集转移；
3. 窑次数相同时，每窑编号升序排列，再将窑次按编号序列排序，
   取整体字典序最小的方案——通过"每一步在保证仍可取得最少窑次的
   前提下，选择编号序列字典序最小的第一窑"贪心重构得到。
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_PIECES = 14


class SchedulingError(ValueError):
    """排程无法完成（如单件器物体积超过单窑容量）。"""


@dataclass(frozen=True)
class Piece:
    piece_id: int
    volume: int
    min_temp: int
    max_temp: int


@dataclass(frozen=True)
class KilnLoad:
    """一窑的烧成方案。"""

    pieces: tuple[int, ...]
    total_volume: int
    firing_temp: int  # 取温度公共交集的下界


def solve(pieces: list[Piece], capacity: int) -> list[KilnLoad]:
    """计算最少窑次且字典序最小的装窑方案。

    无法排程时抛出 :class:`SchedulingError`。
    """
    # ---------- 1. 输入校验 ----------
    if not isinstance(capacity, int) or capacity < 1:
        raise SchedulingError("kiln_capacity 必须为正整数")

    seen: set[int] = set()
    for p in pieces:
        if p.piece_id in seen:
            raise SchedulingError(f"器物编号重复: {p.piece_id}")
        seen.add(p.piece_id)
        if p.volume < 1:
            raise SchedulingError(f"器物 {p.piece_id} 的体积必须为正整数")
        if p.min_temp < 1 or p.max_temp < 1 or p.min_temp > p.max_temp:
            raise SchedulingError(
                f"器物 {p.piece_id} 的温度区间非法: "
                f"需满足 1 <= min_temp({p.min_temp}) <= max_temp({p.max_temp})"
            )
        if p.volume > capacity:
            raise SchedulingError(
                f"器物 {p.piece_id} 体积 {p.volume} 超过单窑容量 {capacity}，无法装窑"
            )

    # 按编号升序排列，位 i 对应第 i 小的编号
    ordered = sorted(pieces, key=lambda p: p.piece_id)
    n = len(ordered)
    size = 1 << n
    full = size - 1

    # ---------- 2. 预计算每个子集的体积、温度交集与可行性 ----------
    valid = bytearray(size)
    volumes = [0] * size
    lows = [0] * size
    highs = [0] * size
    ids_of: list[tuple[int, ...]] = [()] * size

    for i, p in enumerate(ordered):
        bit = 1 << i
        valid[bit] = 1
        volumes[bit] = p.volume
        lows[bit] = p.min_temp
        highs[bit] = p.max_temp
        ids_of[bit] = (p.piece_id,)

    for mask in range(1, size):
        if mask & (mask - 1) == 0:
            continue  # 单件集合已初始化
        low_bit = mask & -mask
        rest = mask ^ low_bit

        ids_of[mask] = ids_of[low_bit] + ids_of[rest]

        total = volumes[rest] + volumes[low_bit]
        if total > capacity:
            continue
        # 公共交集：[各下界的最大值, 各上界的最小值]
        lo = max(lows[rest], lows[low_bit])
        hi = min(highs[rest], highs[low_bit])
        if lo <= hi:
            valid[mask] = 1
            volumes[mask] = total
            lows[mask] = lo
            highs[mask] = hi

    if n == 0:
        return []

    # ---------- 3. 位掩码 DP：最少窑次 ----------
    inf = n + 1
    dp = [inf] * size
    dp[0] = 0
    for mask in range(1, size):
        low_bit = mask & -mask
        sub = mask
        best = inf
        # 第一窑必须包含剩余器物中编号最小者（low_bit），
        # 每个划分只考虑窑按最小编号升序排列的规范形式。
        while sub:
            if (sub & low_bit) and valid[sub]:
                cand = dp[mask ^ sub] + 1
                if cand < best:
                    best = cand
            sub = (sub - 1) & mask
        dp[mask] = best

    if dp[full] >= inf:
        # 单件均不超容量时理论上不可达（每件可单独成窑）
        raise SchedulingError("无法为全部器物安排窑次")

    # ---------- 4. 贪心重构：字典序最小的最优方案 ----------
    remaining = full
    group_masks: list[int] = []
    while remaining:
        low_bit = remaining & -remaining
        sub = remaining
        chosen = 0
        chosen_ids: tuple[int, ...] | None = None
        while sub:
            if (
                (sub & low_bit)
                and valid[sub]
                and dp[remaining ^ sub] + 1 == dp[remaining]
            ):
                ids = ids_of[sub]
                if chosen_ids is None or ids < chosen_ids:
                    chosen_ids = ids
                    chosen = sub
            sub = (sub - 1) & remaining
        if not chosen:
            raise SchedulingError("内部错误：无法重构排程方案")
        group_masks.append(chosen)
        remaining ^= chosen

    # ---------- 5. 组装输出（按窑内最小编号升序） ----------
    loads = [
        KilnLoad(
            pieces=ids_of[group],
            total_volume=volumes[group],
            firing_temp=lows[group],  # 烧成温度取交集下界
        )
        for group in group_masks
    ]
    loads.sort(key=lambda load: load.pieces)
    return loads
