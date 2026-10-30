# Python 刷题速查手册

刷题时撞到什么就补什么。每节：底层是什么 → 常用操作 → 坑。

## list

底层是动态数组：按下标 O(1)，尾部 append/pop 均摊 O(1)，头部插删 O(n)。

```python
a = [3, 1, 2]
a.append(4); a.pop()        # 尾部加/删
a.insert(0, 9)              # 头部插入 O(n)，频繁用请换 deque
a.sort(); sorted(a)         # 原地排序 / 返回新列表
a.sort(key=lambda x: -x)    # 自定义排序键
a[::-1]                     # 反转副本
# 运算符：
a + b                       # 拼接成新列表
a * 3                       # 重复 3 次
[0] * n                     # 定长初始化
grid = [[0] * m for _ in range(n)]   # 二维初始化，别写 [[0] * m] * n
first, *rest = a            # 解包
```

坑：`[[0] * m] * n` 的 n 行是同一个对象，改一行全变。

## str

不可变，每次拼接生成新串。

```python
s.split(); ",".join(parts)
s.strip(); s.startswith("GET")
s.find("x")                 # 找不到返 -1；index 会抛异常
ord("A"); chr(65)
s[::-1]
```

坑：循环里 `s += ch` 是 O(n²)，攒进 list 再 `"".join()`。

## dict / defaultdict / Counter

```python
d.get(k, 0)
for k, v in d.items(): ...
from collections import defaultdict, Counter
cnt = defaultdict(int); cnt[x] += 1
grp = defaultdict(list); grp[key].append(x)
Counter(nums).most_common(3)
```

## set

```python
s = set(); s.add(x); x in s   # O(1)
a & b, a | b, a - b           # 交 / 并 / 差
```

## deque

```python
from collections import deque
q = deque([1, 2, 3])
q.append(4); q.appendleft(0)
q.pop(); q.popleft()          # 两端 O(1)，BFS 用它
```

## 堆 heapq

底层是用 list 表示的完全二叉最小堆，`h[0]` 最小。

```python
import heapq
h = [3, 1, 2]; heapq.heapify(h)   # 原地建堆 O(n)
heapq.heappush(h, 0)              # O(log n)
x = heapq.heappop(h)              # 弹最小 O(log n)
h[0]                              # 看堆顶不弹出
# 大顶堆：存负数
heapq.heappush(h, -x); y = -heapq.heappop(h)
# 元素是元组时按字典序比较（先比第 0 位）
heapq.heappush(pq, (dist, node))  # Dijkstra
```

## bisect

```python
import bisect
i = bisect.bisect_left(a, x)    # 有序数组里 x 的最左插入位置
bisect.insort(a, x)             # 插入并保持有序（O(n)）
```

## 刷题习语

```python
for i, x in enumerate(a): ...
for x, y in zip(a, b): ...
float("inf"); float("-inf")
```
