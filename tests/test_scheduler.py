"""排程算法单元测试（标准库 unittest，无额外依赖）。

运行：python -m unittest discover -s tests -v
"""
import unittest

from app.scheduler import Piece, SchedulingError, solve


def P(pid: int, volume: int, lo: int, hi: int) -> Piece:
    return Piece(piece_id=pid, volume=volume, min_temp=lo, max_temp=hi)


def ids_of(loads):
    return [list(k.pieces) for k in loads]


class SchedulerTest(unittest.TestCase):
    def test_all_in_one_kiln(self):
        # 体积与温度均相容 -> 1 窑，烧成温度取交集下界
        loads = solve([P(1, 3, 1000, 1300), P(2, 2, 900, 1200)], capacity=10)
        self.assertEqual(ids_of(loads), [[1, 2]])
        self.assertEqual(loads[0].total_volume, 5)
        self.assertEqual(loads[0].firing_temp, 1000)

    def test_capacity_split_prefers_smallest_lexicographic(self):
        # 容量 2，均温度相容：[1] 必须单窑，(2,3) 合窑
        loads = solve([P(1, 1, 1000, 1100), P(2, 1, 1000, 1100),
                       P(3, 1, 1000, 1100)], capacity=2)
        self.assertEqual(ids_of(loads), [[1], [2, 3]])
        self.assertEqual(loads[1].firing_temp, 1000)

    def test_temperature_incompatible_split(self):
        # [1000,1050] 与 [1200,1300] 无交集 -> 必须两窑，且小者单窑
        loads = solve([P(5, 1, 1000, 1050), P(6, 1, 1200, 1300)], capacity=10)
        self.assertEqual(ids_of(loads), [[5], [6]])

    def test_intersection_bounds(self):
        # 交集 [1100,1150]，烧成温度取下界 1100
        loads = solve([P(1, 1, 1000, 1200), P(2, 1, 1100, 1300),
                       P(3, 1, 1050, 1150)], capacity=10)
        self.assertEqual(ids_of(loads), [[1, 2, 3]])
        self.assertEqual(loads[0].firing_temp, 1100)

    def test_single_piece_over_capacity(self):
        with self.assertRaises(SchedulingError) as ctx:
            solve([P(1, 11, 1000, 1200)], capacity=10)
        self.assertIn("超过单窑容量", str(ctx.exception))
        self.assertIn("1", str(ctx.exception))

    def test_over_capacity_among_many(self):
        with self.assertRaises(SchedulingError) as ctx:
            solve([P(1, 1, 1000, 1200), P(9, 100, 1000, 1200)], capacity=10)
        self.assertIn("超过单窑容量", str(ctx.exception))

    def test_duplicate_id(self):
        with self.assertRaises(SchedulingError):
            solve([P(1, 1, 1000, 1200), P(1, 1, 1000, 1200)], capacity=10)

    def test_invalid_temperature_range(self):
        with self.assertRaises(SchedulingError):
            solve([P(1, 1, 1300, 1000)], capacity=10)

    def test_minimum_kilns_volume_forced(self):
        # 容量 2：单件分组 [1][2,3][4,5] 可行时字典序更小，
        # 但 [1,2] 合装后仍需 3 窑（(1,2)(3,4)(5)），[1] 仍可 3 窑 -> 取 [1]
        pieces = [P(i, 1, 1000, 1100) for i in range(1, 6)]
        loads = solve(pieces, capacity=2)
        self.assertEqual(len(loads), 3)
        self.assertEqual(ids_of(loads), [[1], [2, 3], [4, 5]])

    def test_minimum_kilns_not_naive_singleton(self):
        # 若 [1] 单窑会导致窑次变多，则 [1] 必须合窑：
        # 容量 2，温度相容，共 4 件最少 2 窑；[1] 单窑则至少 3 窑
        pieces = [P(i, 1, 1000, 1100) for i in range(1, 5)]
        loads = solve(pieces, capacity=2)
        self.assertEqual(len(loads), 2)
        self.assertEqual(ids_of(loads), [[1, 2], [3, 4]])

    def test_non_consecutive_ids_sorted(self):
        loads = solve([P(40, 1, 1200, 1300), P(2, 1, 1000, 1100),
                       P(7, 1, 1000, 1050)], capacity=10)
        # (2,7) 相容，40 不相容；窑序列按窑内最小编号升序
        self.assertEqual(ids_of(loads), [[2, 7], [40]])
        self.assertEqual(loads[0].firing_temp, 1000)
        self.assertEqual(loads[1].firing_temp, 1200)

    def test_max_14_pieces_performance(self):
        import time
        # 全部单件（容量 1）触发最大规模 DP：2^14 状态
        pieces = [P(i, 1, 1000, 1000) for i in range(1, 15)]
        start = time.perf_counter()
        loads = solve(pieces, capacity=1)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(loads), 14)
        self.assertEqual(ids_of(loads), [[i] for i in range(1, 15)])
        self.assertLess(elapsed, 2.0)

    def test_14_pieces_all_compatible(self):
        pieces = [P(i * 3, 1, 1000, 1200) for i in range(1, 15)]
        loads = solve(pieces, capacity=14)
        self.assertEqual(len(loads), 1)
        self.assertEqual(len(loads[0].pieces), 14)
        self.assertEqual(loads[0].total_volume, 14)


if __name__ == "__main__":
    unittest.main()
