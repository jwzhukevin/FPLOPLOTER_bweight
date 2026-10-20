# 首次费米分析后台加载与任务生命周期

2026-10-20；验证环境为 WSL Ubuntu-24.04 的项目 `FPLP`。

## 行为

- 首次进入费米模式只提交 QThread 任务，文件读取、数据校验和自动能窗分析在后台进行。
- Matplotlib 全局样式设置、控制面板和绘图只在 Qt 主线程执行。后台结果移交前移除对 QThread 的取消回调，避免持有已销毁线程。
- 每个加载器最多一个运行任务、一个待启动的最新请求。快速切换不无限创建线程；旧任务协作取消，退出后才启动最新请求。
- 任务代次过滤旧结果、旧错误和旧状态通知；文件切换立即使旧费米结果失效。原有普通文件加载也纳入相同管理，避免其迟到结果回写新文件。
- 状态栏显示忙碌状态并提供“取消加载”。取消费米分析或返回完整模式后恢复完整视图；失败也恢复完整视图，可再次尝试。
- 关闭窗口时取消两个加载器，忽略第一次关闭事件，待全部原生 `QThread.finished` 到达后再关闭。保留线程对象直到退出，不使用线程 `terminate()`，也不在界面线程对加载线程同步 `wait()`。
- 数值层在逐行读取及密度分析循环中检查取消；不改计算公式、数据值、能窗评分或阈值。取消延迟取决于当前步骤何时到达检查点，不能承诺硬实时。

本轮发现并按用户指示保留了并发任务对分组、完整数据读取和显示规则的修改；线程化与当前同步路径比较，没有重新定义这些规则。此前权重基准报告描述的是此前版本，不能作为这些并发显示规则的最终验收。

## 回归与证据

`tests/test_background_loading.py` 使用真实 QThreads 和 Qt 事件循环，覆盖：

- 首次进入费米模式时定时器继续响应，重复模式信号不重复启动；完成后应用最新界面设置。
- 单运行任务、仅最新待启动请求；取消及关闭后拒绝迟到结果、错误、状态。
- 返回完整模式、切换文件、取消按钮、错误后重试。
- 单独绘图组件及主窗口关闭，两个加载器退出前保持宿主对象存活。
- 真实普通/费米后台结果与当前同步读取器的能量、权重和能窗一致。
- 读取中取消、分析循环已开始后取消，以及取消期间异常不显示成用户错误。

线程专项 18 项通过，当前集成版本完整回归 117 项通过。`gui/loading.py` 的 69 条语句和 16 个分支均覆盖，覆盖率 100%。这不代表整个项目或 QThread 内部所有执行行均为 100%；覆盖率默认跟踪对 Qt 原生线程内 Python 执行的统计有限，另外用信号、结果及生命周期断言验证。

三个定向变异（接受过期代次、取消时不发出中断请求、数值层忽略取消）均由断言捕获；导入失败或进程崩溃不计为捕获。变异仅在隔离副本执行，源文件哈希未变。

真实根目录 `+bweights`（约 307 MB）读取阶段的离屏测量：

| 项目 | 测量 |
|---|---:|
| 提交费米任务返回 | 1.77 ms |
| 250 ms 加载期间 Qt 心跳次数 | 25 |
| 最大事件循环间隔 | 10.56 ms |
| 请求取消至加载器空闲 | 0.53 ms |

确认线程退出、未应用费米结果，输入 SHA-256 前后均为 `c510d9b337ca3b18b2b0f655cc989aa9a246d3d19059d80dea8783b728954244`。上述为一次读取阶段响应测量，不是完整分析耗时或可见桌面的帧率保证。

本地证据：`.test-artifacts/background-wsl.json`、`.test-artifacts/coverage-threading.json`、`.test-artifacts/thread-mutation-report.json`。

## 复跑

在 WSL Ubuntu 终端中：

```bash
cd /mnt/d/Code/FPLOPLOTER_bweight
export QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR=/tmp/fplo-test-mpl
export PYTHONPATH="$PWD/.test-artifacts/wsl-test-deps:$PWD"
export COVERAGE_FILE="$PWD/.test-artifacts/.coverage-threading"
FPLP/bin/python -m pytest tests/test_background_loading.py -q -p no:cacheprovider
FPLP/bin/python -m coverage run --branch \
  --source=orbital_data,fplo_visualizer,fplo_fermi_visualizer,gui.tools,gui.loading,gui.main_window,fplo_gui_main \
  -m pytest tests -q -p no:cacheprovider
FPLP/bin/python -m coverage report --include=gui/loading.py,gui/tools.py
FPLP/bin/python scripts/check_weight_mutations.py --scope threading
FPLP/bin/python scripts/check_background_loading.py --data +bweights
```

测试工具复用此前隔离目录；科学计算依赖仍来自现有 FPLP。尚未完成可见 WSL 桌面人工操作验收，也未在真实集群文件系统或正在写入的生产计算目录测试取消延迟。
