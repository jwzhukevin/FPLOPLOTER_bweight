# 权重解析、费米筛选与重绘验证

验证日期：2026-10-20。未修改原始 `+bweights` 数据，未迁移 PyQt5/Matplotlib。

## 修复范围与科学含义

- 两个读取器共用轨道标签解析；重复解析替换分组，不再重复追加列索引。
- 保留“元素 + 主量子数 + s/p/d/f”分组，以及同元素位点、j/m_j 分量求和的定义。未知标签或列数不匹配明确报错，避免后续列错位。
- 修正头部能带数读取：样本原先将第一个整数误报为能带数；现在使用头部的能带数字段，与数据重组得到的数量一致。
- 重要能带包含穿过窗口的相邻采样线段，不再要求至少一个采样点落在窗口内；不插造权重采样点。
- 跨越费米能级的能带不再把离散采样间隔误报为带隙，而返回零带隙。非金属案例保留原有价带顶、导带底之差；未改变材料分类阈值。
- 自动能窗的默认索引限制在数组内，处理窄谱和单能量网格；已有 ±3 eV 等窗口约束不变。
- 工作函数先过滤能窗再执行原有限点规则，修复与单核路径的不一致。

## 重绘优化

分组权重对同一加载数组仅计算一次，按数据数组身份和分组列索引复用；重新读取或解析会失效。数组加载后按只读约定使用，如未来新增原位修改权重的功能，必须同时清理缓存。

每个轨道组合并为一个散点集合，仍逐能带应用原先的阈值、最大点数、权重排序采样及自身最大值归一化。圆点大小不改为绝对权重尺度。

GUI 不再为阈值过滤这样的短任务反复创建进程池；旧多核绘图入口委托给相同路径。控制面板改为显示自动分组缓存，旧工具类仍可供外部调用。

设置和复选框信号在同一轮 Qt 事件中合并；画布在恢复视口后只同步绘制一次。加载另一个文件时清除之前的费米可视化器，避免复用旧数据。

## 指定环境与复跑

最终验证使用 WSL `Ubuntu-24.04` 中本项目的 `FPLP/bin/python`：Python 3.12.3、NumPy 2.3.2、Matplotlib 3.10.5、PyQt5 5.15.11。

以下命令在 Ubuntu 终端运行：

```bash
cd /mnt/d/Code/FPLOPLOTER_bweight
# 测试工具隔离在忽略目录，不替换 FPLP 内的科学计算依赖。
FPLP/bin/python -m pip install --target .test-artifacts/wsl-test-deps pytest coverage radon
export PYTHONPATH="$PWD/.test-artifacts/wsl-test-deps:$PWD"
export QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR=/tmp/fplo-test-mpl
export COVERAGE_FILE="$PWD/.test-artifacts/.coverage"
FPLP/bin/python -m coverage run --branch \
  --source=orbital_data,fplo_visualizer,fplo_fermi_visualizer,gui.tools,fplo_gui_main \
  -m pytest tests -q -p no:cacheprovider
FPLP/bin/python -m coverage report -m
FPLP/bin/python -m radon cc orbital_data.py -s
FPLP/bin/python scripts/check_weight_mutations.py
FPLP/bin/python scripts/benchmark_weights.py --baseline-ref 3254360 \
  --data +bweights --repeats 7 --output .test-artifacts/benchmark-wsl.json \
  --preview-dir .test-artifacts/figures
```

## 已验证证据

- 39 项回归通过，包括两个读取器、构造后再次分析、金属/绝缘体、移动参考能级、窄谱、非法输入、缓存失效、单/多核入口一致性、Qt 信号合并和真实离屏渲染。
- 五份本地科学数据的表头列映射与求和守恒通过；这些额外测试在未携带本地数据的副本中不会运行，通用回归使用自包含小数据。
- `orbital_data.py`：55 条语句、22 个分支均覆盖，合计覆盖率 100%；圈复杂度为 3、3、4、9。本次纳入统计的五个模块合计覆盖率为 49.25%，不是旧项目整体覆盖率 100%。
- 9 个定向变异全部由测试捕获：重复索引、未知列错位、遗漏窗口穿越、金属伪带隙、边界溢出、错误求和、忽略能窗、改变点大小归一化、重复重绘。副本内执行，源文件哈希未变；这不是全仓库穷举变异测试。
- `git diff --check` 通过。Git 的 LF/CRLF 转换提示与空白错误分开记录。

真实数据基准：原始 414 个 k 点、208 条能带，沿用 GUI 原有采样后为 207 个 k 点；22 组，窗口 −5～5 eV，阈值 0.02。预热后重复 7 次取中位数，对比修复前提交 `3254360` 的单核路径：

| 项目 | 原实现 | 优化后 |
|---|---:|---:|
| 准备数据及创建散点集合 | 139.99 ms | 28.86 ms |
| 单次 Agg 画布渲染 | 97.44 ms | 78.11 ms |
| 散点集合 | 152 | 9 |
| 绘制点数 | 14,025 | 14,025 |

准备与渲染合计约 237.43 → 106.96 ms，减少约 55%。此微基准不包含文件读取、骨架、图例、布局、Qt 事件和进程启动，也未把移除的第二次绘制计入收益，不能换算为完整 GUI 帧率。

优化前后点坐标、点大小在 `1e-12` 容差内一致；该离屏图像像素平均绝对差为 0。真实输入 SHA-256 在基准前后均为 `c510d9b337ca3b18b2b0f655cc989aa9a246d3d19059d80dea8783b728954244`。

## 保留限制

未改动 k 点采样策略、投影基底、权重阈值和自动窗口评分。沿 k 路径得到的金属/带隙判断不是整个布里渊区收敛证明；采样之外的极值仍可能漏掉。

首次切换费米模式仍会读取文件并执行原有分析，尚未改成后台线程。未进行可见 WSL 桌面的人工操作验收或完整导出功能验收；Qt 离屏测试与 Agg 微基准不等同于真实桌面交互性能。旧 GUI/导出模块的整体覆盖率仍较低，未做全仓库变异或 CRAP 审计。
