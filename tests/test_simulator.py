import unittest
from vm_simulator import parse_references, simulate

class SimulatorTests(unittest.TestCase):
    def test_dirty_state_write_hit_read_eviction_reload(self):
        refs = parse_references("1:R 1:W 1:R 2:R 3:R 1:R")
        trace, summary = simulate(refs, 2, "fifo")
        # Step 2 is a write hit; step 3 read hit must retain dirty state.
        self.assertEqual(trace[1]["result"], "HIT")
        self.assertEqual(trace[1]["frame_0"], "1/D")
        self.assertEqual(trace[2]["frame_0"], "1/D")
        # Step 5 evicts dirty page 1; step 6 reloads it clean.
        self.assertEqual(trace[4]["victim"], "1")
        self.assertEqual(trace[4]["dirty_writeback"], "yes")
        self.assertEqual(trace[5]["result"], "FAULT")
        self.assertIn("1/C", [trace[5][f"frame_{i}"] for i in range(2)])
        self.assertEqual(summary["dirty_writebacks"], 1)

    def test_same_faults_different_writebacks(self):
        refs = parse_references("0:R 0:R 1:R 0:W 2:R")
        _, fifo = simulate(refs, 2, "fifo")
        _, lru = simulate(refs, 2, "lru")
        self.assertEqual(fifo["faults"], lru["faults"])
        self.assertEqual(fifo["faults"], 3)
        self.assertEqual(fifo["dirty_writebacks"], 1)
        self.assertEqual(lru["dirty_writebacks"], 0)
        self.assertGreater(fifo["total_modeled_time_us"], lru["total_modeled_time_us"])

    def test_input_validation(self):
        for bad in ("", "1:X", "-1:R", "1000:R", "1:R " * 257):
            with self.assertRaises(ValueError):
                parse_references(bad)

    def test_basic_invariants_all_policies(self):
        refs = parse_references("7:R 0:W 1:R 2:W 0:R 3:R 0:W 4:R")
        for policy in ("fifo", "lru", "opt", "clock"):
            trace, summary = simulate(refs, 3, policy)
            self.assertEqual(summary["hits"] + summary["faults"], 8)
            self.assertLessEqual(summary["dirty_writebacks"], summary["evictions"])
            self.assertLessEqual(summary["evictions"], summary["faults"])
            self.assertEqual(len(trace), 8)

if __name__ == "__main__":
    unittest.main()
