# 人工轨道检查的可信度改进与验证

日期：2026-10-20。此次修改不接入自动轨道筛选，不修改原始 FPLO 文件、不提交 Git。

## 修改范围与科学含义

1. `orbital_data.py` 保留每列的原始轨道标签、元素、原子编号、壳层与 SOC 分量。显示分组由元素/壳层改为原子/壳层，只累加同原子同壳层的分量；不依据编号推断对称等价性。
2. GUI、完整能带导出与费米附近导出共用原始权重面积映射。默认面积为 `2 + 48 * W`（points²），GUI 的点面积和系数设置会同时作用于所有轨道及标尺。权重超过 1 时继续线性显示，不裁剪为 1；原始数值没有归一化。
3. 原有完整能带图片导出中的插值权重点改为原始采样点，避免人工查看时把插值结果当作计算数据。能带线仍连接原始能量采样。
4. 两个读取器共用完整性校验，不再通过 k=0 行数推断能带数或整除丢弃末尾状态。以声明的 k 点数、能带数和权重列数校验完整数据；允许重复路径坐标及非零路径起点。
5. 数据读取后为完整、只读 NumPy 数组。`read_and_parse_data(max_kpoints=...)` 的参数只记录绘图上限，不删减数据。GUI 加载不设置隐藏的 200 点上限，使用控制面板中的显示预算。
6. 绘图先按能窗、视口和显示阈值过滤，再限制当前视口内每个轨道/能带的点数。限点采用保持顺序与两端的等间隔取点；预算为 1 时保留最大权重点。总览可能省略局部特征，放大可从完整数据恢复，图中明确标注全量 k 点数和显示上限。

保留原有能量参考约定（相对 EF 的 eV），不改变温度、物理窗口、阈值、权重数值或原始科学数据。负权重保留并提示；正阈值散点仍只显示超过阈值的正权重。文件头/负载一致、文件读取期间未变化，不代表 FPLO 已自洽、导出轨道完整或 Wannier/BCD 已验证。

## 与现有工作的兼容

修改前源码及未跟踪测试已复制到忽略目录 `.test-artifacts/manual-review-baseline-20261020-165504/`，附 SHA-256 清单。工作区并发增加的后台加载、取消及错误处理逻辑均保留，新的读取循环支持已有取消回调。

原有断言中的跨原子合并和逐能带最大值归一化，按本次用户要求更新为逐原子分组及统一原始权重标尺；未删除有效测试、降低阈值或跳过测试。没有修改依赖或系统环境。

## 实际验证

- 使用现有 WSL `Ubuntu-24.04` 的 `FPLP/bin/python`，Python 3.12.3，Qt 离屏平台。修改前测试基线为 39 项通过；最终完整回归 117 项通过，包含同时存在的后台加载回归。
- 覆盖正常、损坏头部、截断一行/一组 k 点、额外状态、错列、NaN/Inf、非法数字、块内坐标不一致、倒序路径、读中变化、读取取消、失败重载保护、非零起点、重复坐标和负权重保留。
- 真实 Qt 控件验证独立原子开关、原始标签提示、统一权重大小、显示限点、Shift 框选与工具栏视口变化后重新取点；完整/费米两种绘图模式均覆盖局部特征恢复。
- 新增公共模块 `orbital_data.py` 和 `weight_plot.py` 的语句与分支覆盖率均为 100%。这是模块覆盖率，不代表整个应用全覆盖；本轮公共函数最高圈复杂度 10。
- 8 项定向变异针对原子误合并、逐组重新归一化、非有限输入放行、截断放行、块坐标漏检、完整数组被抽样、忽略局部视口、丢弃显示端点；在隔离副本运行，报告位于 `.test-artifacts/manual-review-mutation-report.json`。这不是穷举变异测试。
- 5 份真实 FPLO 文件均完整加载，并使用独立 `numpy.loadtxt` 比较每个原始能量与 k 坐标；所有原子壳层分组之和与原始权重总和一致。验证前后原始文件 SHA-256 不变。

| 数据文件 | 保留 k 点 | 能带数 | 权重列 | 原子壳层数 |
|---|---:|---:|---:|---:|
| 根目录 `+bweights` | 414 | 208 | 208 | 38 |
| `10585_Sr2PRh/+bweights` | 462 | 148 | 148 | 28 |
| `10971_V2GaN/+bweights` | 270 | 148 | 148 | 28 |
| `19606_BaCu2P/+bweights` | 560 | 138 | 138 | 27 |
| `6070_LaCuP2/+bweights` | 456 | 158 | 158 | 29 |

实际主窗口渲染选择了 `Br(003)_4p`、`Br(004)_4p`、`Br(005)_4p` 与 `Ag(002)_4d`，查看 ±2 eV 区域。窗口截图及 PNG/PDF/SVG 位于 `.test-artifacts/manual-review-validation/`；`validation.json` 包含原始输入和实际运行源码的 SHA-256、全量形状及读取时间。PNG 和实际窗口截图已经视觉检查。

尚未验证 Windows 原生桌面交互、打包可执行文件、其他 FPLO 版本/全部标签格式、集群在线读取、实际 Wannier 投影和 BCD。检查不监控加载完成后的源文件更新，之后更新来源需要重新加载。

## 复跑

在 WSL 项目目录执行，复用已存在的虚拟环境及测试依赖，不安装或升级依赖：

```bash
export PYTHONPATH="$PWD/.test-artifacts/wsl-test-deps:$PWD"
export QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR=/tmp/fplo-test-mpl
export COVERAGE_FILE="$PWD/.test-artifacts/.coverage-manual-review"
FPLP/bin/python -m coverage run --branch \
  --source=orbital_data,weight_plot,fplo_visualizer,fplo_fermi_visualizer,fplo_gui_main,gui.tools \
  -m pytest tests -q -p no:cacheprovider
FPLP/bin/python -m coverage json -o .test-artifacts/manual-review-coverage.json
FPLP/bin/python -m radon cc orbital_data.py weight_plot.py -s
FPLP/bin/python scripts/check_weight_mutations.py --scope manual-review
FPLP/bin/python scripts/validate_manual_review.py --output .test-artifacts/manual-review-validation
```
