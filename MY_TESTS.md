# my-designed tests and expected reasoning

## Test 1 — Dirty-state retention and reload

**Policy:** FIFO  
**Capacity:** 1 frame  
**Sequence:** `0:R 0:W 0:R 1:R 0:R 2:R`

**Expected trace:**

1. `0:R`: Page fault; load page 0 into the frame as clean.
2. `0:W`: Write hit; page 0 becomes dirty.
3. `0:R`: Read hit; page 0 remains dirty.
4. `1:R`: Page fault; FIFO evicts page 0. Since page 0 is dirty, one writeback occurs. Page 1 is loaded as clean.
5. `0:R`: Page fault; FIFO evicts page 1, which is clean. Page 0 is reloaded as clean.
6. `2:R`: Page fault; FIFO evicts page 0, which is now clean. Page 2 is loaded as clean.

**Expected totals:**

- Total references (N): 6
- Hits: 2
- Page faults: 4
- Evictions: 3
- Dirty writebacks: 1

**Expected final state:** Page 2 is resident and clean. Page 0 was written back when it was first evicted and was subsequently reloaded as a clean page.

## Test 2 — Same Faults, Different Writeback Costs

**Capacity:** 2 frames  
**Policies:** FIFO and LRU  
**Sequence:** `0:R 1:R 0:W 2:R`

### FIFO

1. `0:R`: Page fault; load page 0 as clean.
2. `1:R`: Page fault; load page 1 as clean.
3. `0:W`: Write hit; page 0 becomes dirty. FIFO order remains page 0, then page 1.
4. `2:R`: Page fault; FIFO evicts page 0 (the oldest loaded page). Since page 0 is dirty, one writeback occurs. Page 2 is loaded as clean.

### LRU

1. `0:R`: Page fault; load page 0 as clean.
2. `1:R`: Page fault; load page 1 as clean.
3. `0:W`: Write hit; page 0 becomes dirty and most recently used.
4. `2:R`: Page fault; LRU evicts page 1 (the least recently used page). Since page 1 is clean, no writeback occurs. Page 2 is loaded as clean.

### Expected Results

Both policies:
- Total references (N): 4
- Hits: 1
- Page faults: 3
- Evictions: 1

Writebacks:
- FIFO: 1 dirty writeback.
- LRU: 0 dirty writebacks.

### Modeled Cost

Using the cost model:

`Total cost = N × m + F × Tin + D × Tout`

Where:
- `m = 1 μs`
- `Tin = 10,000 μs`
- `Tout = 10,000 μs`

**FIFO:**

`4 × 1 + 3 × 10,000 + 1 × 10,000 = 40,004 μs`

**LRU:**

`4 × 1 + 3 × 10,000 + 0 × 10,000 = 30,004 μs`

This test demonstrates that two page-replacement policies can produce the same number of page faults but different modeled execution costs because of their different dirty-page writeback counts.