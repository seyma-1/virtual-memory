# Ubuntu experiment results

**Environment type:** WSL2 (Ubuntu running on Windows)  
**Ubuntu release:** Ubuntu 26.04.1 LTS (`resolute`)  
**Kernel:** 6.18.58.1-microsoft-standard-WSL2  
**Page size:** 4096 bytes  
**Compiler:** cc (Ubuntu 15.2.0-16ubuntu1) 15.2.0  

## First touch

**Prediction before running:**
- **Mapping:** Expected no page faults because `mmap()` creates the virtual memory mapping without necessarily allocating physical pages.
- **First read:** Expected minor page faults when the program first accesses the pages. No major page faults were expected.
- **First write:** Expected additional minor page faults as writable private pages are allocated on first write.
- **Repeated write:** Expected no additional page faults because the pages should already be resident and writable.

| Fresh process | Mapping minor/major delta | First-read minor/major delta | First-write minor/major delta | Repeated-write minor/major delta |
|---|---|---|---|---|
| 1 | 0 / 0 | 4096 / 0 | 4096 / 0 | 0 / 0 |
| 2 | 0 / 0 | 4096 / 0 | 4096 / 0 | 0 / 0 |
| 3 | 0 / 0 | 4096 / 0 | 4096 / 0 | 0 / 0 |

**Interpretation and differences from prediction:**

The three runs produced identical results.

The mapping operation produced zero minor and major page faults. This is consistent with lazy allocation: creating a virtual memory mapping does not necessarily allocate physical memory immediately.

The first read produced 4096 minor page faults and zero major page faults. This is consistent with the operating system handling the first access to the mapped pages. One possible explanation for anonymous memory is the use of a shared zero page, although these counters alone do not prove that mechanism.

The first write produced another 4096 minor page faults and zero major page faults. This is consistent with the allocation of private writable pages when the program writes to the memory for the first time.

The repeated write produced zero additional page faults because the pages had already been accessed and made writable.

Overall, the observed results matched the predictions. No major page faults were observed in these runs.

## Copy on write

**Prediction before running:**
- **Parent value:** Expected to remain 7 after the child modifies its private memory.
- **Child value:** Expected to become 9 after the child writes to its private memory.

| Fresh process | Raw output | Parent value | Child value |
|---|---|---|---|
| 1 | `child_private_value=9 parent_private_value=7` | 7 | 9 |
| 2 | `child_private_value=9 parent_private_value=7` | 7 | 9 |
| 3 | `child_private_value=9 parent_private_value=7` | 7 | 9 |

**What printed values establish:**

All three runs produced the same output. The child process observed the value 9 after modifying its private memory, while the parent process still observed the original value 7.

This behavior is consistent with Copy-on-Write (COW): after the processes initially share memory, a write by the child is handled privately, so the parent's value remains unchanged.

**What they cannot establish about physical frame identities or exact copy timing:**

The printed values demonstrate the different values observed by the parent and child processes. However, they do not identify the physical memory frame numbers used by either process.

They also do not reveal the exact moment when the operating system performed the physical page copy. The output is consistent with COW behavior, but it does not directly show the internal memory-management operations.