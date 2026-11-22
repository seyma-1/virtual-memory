mkdir -p results

{
  echo "===== /etc/os-release ====="
  cat /etc/os-release
  echo "===== kernel ====="
  uname -r
  echo "===== page size ====="
  getconf PAGESIZE
  echo "===== compiler ====="
  cc --version
} 2>&1 | tee results/environment.txt

cc -std=c11 -O2 -Wall -Wextra first-touch.c -o first-touch
cc -std=c11 -O2 -Wall -Wextra cow-observe.c -o cow-observe

for run in 1 2 3; do
  echo "===== first-touch run ${run} =====" | tee "results/first-touch-${run}.txt"
  ./first-touch 2>&1 | tee -a "results/first-touch-${run}.txt"
done

for run in 1 2 3; do
  echo "===== cow-observe run ${run} =====" | tee "results/cow-observe-${run}.txt"
  ./cow-observe 2>&1 | tee -a "results/cow-observe-${run}.txt"
done
