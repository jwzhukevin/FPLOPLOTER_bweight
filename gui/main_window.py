# -*- coding: utf-8 -*-
"""
主窗口模块：
- MainWindow: 应用程序主窗口

注意：为避免循环依赖，本模块从 fplo_gui_main 导入 ControlPanel 与
InteractivePlotWidget，而 fplo_gui_main 不在模块顶层导入 MainWindow，
而是在 main() 内部延迟导入。
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QFileDialog,
    QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt

from log_manager import (
    logger, log_info, log_warning, log_error, log_critical,
    log_status, log_user_action, log_performance, log_data_info, log_debug
)

# 来自项目内模块
from gui.log_widget import LogWidget
from gui.tools import DataLoaderThread
# 注意：以下从主文件导入，需确保主文件不在顶层导入 MainWindow
from fplo_gui_main import ControlPanel, InteractivePlotWidget


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 初始化属性
        self.current_filename = None  # 当前加载的文件名

        # 性能监控进程管理
        self.performance_monitor_process = None

        # 连接到日志管理器
        self.logger = logger

        # 记录程序启动
        log_status("FPLO可视化工具主窗口初始化")

        self.init_ui()

    def set_window_icon(self):
        """设置窗口图标"""
        from PyQt5.QtGui import QIcon
        import os

        icon_paths = [
            "icon.png",
            "icon.ico",
            "assets/icon.png",
            "assets/icon.ico",
            "images/icon.png",
            "images/icon.ico",
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        print(f"成功加载自定义图标: {icon_path}")
                        return
                except Exception as e:
                    print(f"加载图标失败 {icon_path}: {e}")
                    continue

        self.create_default_icon()

    def create_default_icon(self):
        """创建默认图标"""
        from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QPen, QFont
        from PyQt5.QtCore import Qt

        try:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            painter.setBrush(QBrush(QColor(70, 130, 180)))
            painter.setPen(QPen(QColor(25, 25, 112), 2))
            painter.drawEllipse(2, 2, 28, 28)

            painter.setPen(QPen(Qt.white))
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "F")

            painter.end()

            icon = QIcon(pixmap)
            self.setWindowIcon(icon)
            print("使用默认生成的图标")

        except Exception as e:
            print(f"创建默认图标失败: {e}")

    def init_ui(self):
        self.setWindowTitle("FPLO能带权重可视化工具")
        self.set_window_icon()

        try:
            screen = self.screen() or self.windowHandle().screen() or None
            if screen is None:
                raise RuntimeError("无法获取屏幕信息")
            screen_geometry = screen.geometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            window_width = min(1400, int(screen_width * 0.8))
            window_height = min(900, int(screen_height * 0.8))
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.setGeometry(x, y, window_width, window_height)
            print(f"窗口大小: {window_width}x{window_height}")
        except Exception as e:
            self.setGeometry(100, 100, 1200, 800)
            print(f"使用默认窗口大小: {e}")

        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()

        self.plot_splitter = QSplitter(Qt.Vertical)
        self.plot_widget = InteractivePlotWidget()
        self.plot_splitter.addWidget(self.plot_widget)

        self.log_widget = LogWidget()
        self.plot_splitter.addWidget(self.log_widget)
        self.plot_splitter.setSizes([700, 150])

        self.control_panel = ControlPanel()
        self.control_panel.setMaximumWidth(350)

        self.control_panel.orbital_toggled.connect(self.plot_widget.toggle_orbital_visibility)
        self.control_panel.view_mode_changed.connect(self.plot_widget.set_view_mode)
        self.control_panel.settings_changed.connect(self.plot_widget.update_plot_settings)

        self.plot_widget.control_panel_ref = self.control_panel

        self.main_layout = main_layout
        main_layout.addWidget(self.plot_splitter, 3)
        main_layout.addWidget(self.control_panel, 1)

        self.control_panel_visible = True
        self.log_widget_visible = True

        central_widget.setLayout(main_layout)

        self.create_menu_bar()
        self.statusBar().showMessage("就绪")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

        self.log_widget.log_info("程序启动完成")

    def toggle_control_panel(self):
        """切换控制面板显示/隐藏"""
        if self.control_panel_visible:
            self.control_panel.hide()
            self.control_panel_visible = False
            self.log_widget.log_info("控制面板已隐藏")
        else:
            self.control_panel.show()
            self.control_panel_visible = True
            self.log_widget.log_info("控制面板已显示")

    def toggle_log_widget(self):
        """切换日志区域显示/隐藏"""
        if self.log_widget_visible:
            self.log_widget.hide()
            self.log_widget_visible = False
            self.plot_splitter.setSizes([850, 0])
        else:
            self.log_widget.show()
            self.log_widget_visible = True
            self.plot_splitter.setSizes([700, 150])
            self.log_widget.log_info("日志区域已显示")

    def create_menu_bar(self):
        """创建美化的菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #d0d0d0;
                font-size: 14px;
                font-weight: bold;
                padding: 2px;
                min-height: 28px;
            }
            QMenuBar::item { background-color: transparent; padding: 4px 10px; margin: 1px; border-radius: 3px; }
            QMenuBar::item:selected { background-color: #e0e0e0; border: 1px solid #c0c0c0; }
            QMenuBar::item:pressed { background-color: #d0d0d0; }
            QMenu { background-color: #f8f8f8; border: 1px solid #d0d0d0; border-radius: 4px; font-size: 13px; padding: 2px; }
            QMenu::item { background-color: transparent; padding: 4px 12px; margin: 1px; border-radius: 3px; }
            QMenu::item:selected { background-color: #e0e0e0; border: 1px solid #c0c0c0; }
            QMenu::item:pressed { background-color: #d0d0d0; }
            QMenu::separator { height: 1px; background-color: #d0d0d0; margin: 2px 0px; }
        """)

        file_menu = menubar.addMenu('文件')
        open_action = file_menu.addAction('打开FPLO文件...')
        open_action.setShortcut('Ctrl+O')
        open_action.setStatusTip('打开FPLO +bweight文件进行分析')
        open_action.triggered.connect(self.open_file)
        file_menu.addSeparator()

        export_submenu = file_menu.addMenu('导出图像')
        export_submenu.setStatusTip('将当前图形导出为不同格式和清晰度')
        png_submenu = export_submenu.addMenu('PNG格式')
        png_standard_action = png_submenu.addAction('标准清晰度 (150 DPI)')
        png_standard_action.setStatusTip('导出标准清晰度PNG，适合网页和演示')
        png_standard_action.triggered.connect(lambda: self.export_image_with_quality('png', 'standard'))
        png_high_action = png_submenu.addAction('高清晰度 (300 DPI)')
        png_high_action.setStatusTip('导出高清晰度PNG，适合打印和发表')
        png_high_action.triggered.connect(lambda: self.export_image_with_quality('png', 'high'))
        png_ultra_action = png_submenu.addAction('超高清晰度 (600 DPI)')
        png_ultra_action.setStatusTip('导出超高清晰度PNG，适合大尺寸打印')
        png_ultra_action.triggered.connect(lambda: self.export_image_with_quality('png', 'ultra'))
        export_pdf_action = export_submenu.addAction('PDF格式 (矢量)')
        export_pdf_action.setStatusTip('导出矢量PDF，适合学术发表')
        export_pdf_action.triggered.connect(lambda: self.export_image('pdf'))
        export_svg_action = export_submenu.addAction('SVG格式 (可编辑)')
        export_svg_action.setStatusTip('导出可编辑的SVG矢量图')
        export_svg_action.triggered.connect(lambda: self.export_image('svg'))
        file_menu.addSeparator()
        exit_action = file_menu.addAction('退出程序')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('退出FPLO可视化工具')
        exit_action.triggered.connect(self.close)

        view_menu = menubar.addMenu('视图')
        complete_action = view_menu.addAction('完整能带结构')
        complete_action.setShortcut('Ctrl+1')
        complete_action.setStatusTip('显示完整的能带结构')
        complete_action.triggered.connect(lambda: self.switch_view('complete'))
        fermi_action = view_menu.addAction('费米面专注模式')
        fermi_action.setShortcut('Ctrl+2')
        fermi_action.setStatusTip('专注显示费米能级附近的能带')
        fermi_action.triggered.connect(lambda: self.switch_view('fermi'))
        view_menu.addSeparator()
        zoom_info_action = view_menu.addAction('框选放大 (Shift+拖拽)')
        zoom_info_action.setEnabled(False)
        zoom_info_action.setStatusTip('按住Shift键并拖拽鼠标进行框选放大')
        reset_zoom_action = view_menu.addAction('重置缩放')
        reset_zoom_action.setShortcut('Ctrl+R')
        reset_zoom_action.setStatusTip('重置到完整视图')
        reset_zoom_action.triggered.connect(self.control_panel.reset_zoom)
        view_menu.addSeparator()
        refresh_action = view_menu.addAction('刷新图形')
        refresh_action.setShortcut('F5')
        refresh_action.setStatusTip('重新绘制当前图形')
        refresh_action.triggered.connect(self.refresh_plot)
        view_menu.addSeparator()
        toggle_panel_action = view_menu.addAction('切换控制面板')
        toggle_panel_action.setShortcut('Ctrl+P')
        toggle_panel_action.setStatusTip('显示/隐藏右侧控制面板')
        toggle_panel_action.triggered.connect(self.toggle_control_panel)
        toggle_log_action = view_menu.addAction('切换日志区域')
        toggle_log_action.setShortcut('Ctrl+L')
        toggle_log_action.setStatusTip('显示/隐藏底部日志区域')
        toggle_log_action.triggered.connect(self.toggle_log_widget)

        orbital_menu = menubar.addMenu('轨道控制')
        select_all_action = orbital_menu.addAction('全选轨道')
        select_all_action.setShortcut('Ctrl+A')
        select_all_action.setStatusTip('选中所有轨道进行显示')
        select_all_action.triggered.connect(self.control_panel.select_all_orbitals)
        deselect_all_action = orbital_menu.addAction('全不选轨道')
        deselect_all_action.setShortcut('Ctrl+D')
        deselect_all_action.setStatusTip('取消选中所有轨道')
        deselect_all_action.triggered.connect(self.control_panel.deselect_all_orbitals)
        invert_action = orbital_menu.addAction('反选轨道')
        invert_action.setShortcut('Ctrl+I')
        invert_action.setStatusTip('反转当前轨道选择状态')
        invert_action.triggered.connect(self.control_panel.invert_orbital_selection)

        style_menu = menubar.addMenu('样式')
        academic_action = style_menu.addAction('学术标准')
        academic_action.setStatusTip('使用学术发表标准的颜色方案')
        academic_action.triggered.connect(self.set_academic_style)
        colorful_action = style_menu.addAction('多彩模式')
        colorful_action.setStatusTip('使用丰富多彩的颜色方案')
        colorful_action.triggered.connect(self.set_colorful_style)
        monochrome_action = style_menu.addAction('单色模式')
        monochrome_action.setStatusTip('使用灰度单色方案')
        monochrome_action.triggered.connect(self.set_monochrome_style)

        tools_menu = menubar.addMenu('工具')
        # [Deprecated 20250827] 旧逻辑：清除缓存菜单项已移除（缓存机制废弃，采用全量重绘）
        performance_action = tools_menu.addAction('性能监控')
        performance_action.setStatusTip('打开性能监控工具')
        performance_action.triggered.connect(self.open_performance_monitor)

        help_menu = menubar.addMenu('帮助')
        usage_action = help_menu.addAction('使用说明')
        usage_action.setShortcut('F1')
        usage_action.setStatusTip('查看详细使用说明')
        usage_action.triggered.connect(self.show_usage_guide)
        shortcuts_action = help_menu.addAction('快捷键')
        shortcuts_action.setStatusTip('查看所有快捷键')
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addSeparator()
        about_action = help_menu.addAction('关于程序')
        about_action.setStatusTip('查看程序信息和版本')
        about_action.triggered.connect(self.show_about_dialog)

    def open_file(self):
        """打开文件"""
        log_user_action("打开文件对话框")
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择+bweight文件", "", "FPLO文件 (*+bweight*);;所有文件 (*)")
        if filename:
            log_user_action("选择文件", filename)
            log_info(f"开始加载文件: {filename}")
            self.current_filename = filename
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.loader_thread = DataLoaderThread(filename)
            self.loader_thread.progress.connect(self.progress_bar.setValue)
            self.loader_thread.status.connect(lambda msg: log_info(msg))
            self.loader_thread.finished.connect(self.on_data_loaded)
            self.loader_thread.error.connect(self.on_load_error)
            self.loader_thread.start()
        else:
            log_user_action("取消文件选择")

    def on_data_loaded(self, visualizer):
        """数据加载完成"""
        self.progress_bar.setVisible(False)
        elements = sorted(visualizer.elements)
        orbital_types = sorted(visualizer.orbital_types)
        logger.set_system_info(self.current_filename, elements)
        self.plot_widget.set_visualizer(visualizer, self.current_filename)
        self.control_panel.set_orbitals(visualizer)
        log_info(f"数据加载完成！")
        log_data_info("元素种类", f"{len(elements)} 种: {', '.join(elements)}")
        log_data_info("轨道类型", f"{len(orbital_types)} 种: {', '.join(orbital_types)}")
        log_data_info("轨道组合", f"总计 {len(visualizer.orbital_info)} 个")
        for orbital_key, indices in visualizer.orbital_info.items():
            element, orbital_type = orbital_key.split('_')
            color = visualizer.orbital_colors.get(orbital_key, '#95A5A6')
            self.log_widget.log_info(f"  {element} {orbital_type}: {len(indices)} 个权重, 颜色: {color}")
        log_info("可以开始分析，使用右侧面板控制显示")
        self.statusBar().showMessage(f"数据已加载 - {len(elements)} 元素, {len(orbital_types)} 轨道类型")

    def on_load_error(self, error_msg):
        """数据加载错误"""
        self.progress_bar.setVisible(False)
        log_error(f"文件加载失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"文件加载失败:\n{error_msg}")

    def switch_view(self, view_type):
        """切换视图 - 支持新的视图切换系统"""
        log_user_action("菜单切换视图", view_type)
        log_info(f"切换到{view_type}视图")
        if hasattr(self.control_panel, 'set_view_mode_programmatically'):
            self.control_panel.set_view_mode_programmatically(view_type)
        if hasattr(self.plot_widget, 'set_view_mode'):
            self.plot_widget.set_view_mode(view_type)

    def closeEvent(self, event):
        """程序关闭事件 - 保存日志并关闭子进程"""
        import subprocess
        log_status("程序正在关闭...")
        log_user_action("关闭程序")
        if self.performance_monitor_process and self.performance_monitor_process.poll() is None:
            log_info("正在关闭性能监控进程...")
            try:
                self.performance_monitor_process.terminate()
                self.performance_monitor_process.wait(timeout=3)
                log_info("性能监控进程已关闭")
            except subprocess.TimeoutExpired:
                log_warning("性能监控进程未响应，强制关闭")
                self.performance_monitor_process.kill()
            except Exception as e:
                log_error(f"关闭性能监控进程时出错: {e}")
        logger.finalize_log()
        event.accept()

    def refresh_plot(self):
        """刷新图形"""
        if self.plot_widget.visualizer:
            self.plot_widget.plot_current_view()
            self.log_widget.log_info("图形已刷新")

    def set_academic_style(self):
        settings = {'color_scheme': 'academic'}
        self.plot_widget.update_plot_settings(settings)
        self.log_widget.log_info("已切换到学术标准样式")

    def set_colorful_style(self):
        settings = {'color_scheme': 'colorful'}
        self.plot_widget.update_plot_settings(settings)
        self.log_widget.log_info("已切换到多彩样式")

    def set_monochrome_style(self):
        settings = {'color_scheme': 'monochrome'}
        self.plot_widget.update_plot_settings(settings)
        self.log_widget.log_info("已切换到单色样式")

    def open_performance_monitor(self):
        """打开性能监控工具 - 随程序关闭而停止"""
        try:
            import subprocess, sys
            if self.performance_monitor_process and self.performance_monitor_process.poll() is None:
                log_info("关闭已有的性能监控进程")
                self.performance_monitor_process.terminate()
                self.performance_monitor_process = None
            python_cmd = sys.executable
            self.performance_monitor_process = subprocess.Popen([python_cmd, 'performance_monitor.py'])
            log_info("性能监控工具已启动，将随主程序关闭而停止")
        except FileNotFoundError:
            log_error("找不到performance_monitor.py文件")
            QMessageBox.warning(self, "警告", "找不到performance_monitor.py文件")
        except Exception as e:
            log_error(f"无法启动性能监控: {str(e)}")
            QMessageBox.warning(self, "警告", f"无法启动性能监控工具:\n{str(e)}\n\n建议运行: pip install psutil")

    def show_usage_guide(self):
        usage_text = """
        <h2>FPLO可视化工具使用指南</h2>
        <h3>快速开始</h3>
        <p>1. 点击 <b>打开FPLO文件</b> 加载+bweight文件</p>
        <p>2. 在右侧面板控制轨道显示</p>
        <p>3. 使用 <b>Shift+拖拽</b> 进行框选放大</p>
        <h3>轨道控制</h3>
        <p>• 每个轨道显示为: <b>元素 轨道类型 (权重数量)</b></p>
        <p>• 复选框颜色对应轨道在图中的颜色</p>
        <p>• 支持全选、全不选、反选操作</p>
        <h3>视图模式</h3>
        <p>• <b>完整能带结构</b>: 显示所有能带</p>
        <p>• <b>费米面专注模式</b>: 只显示费米能级附近</p>
        <h3>样式选择</h3>
        <p>• <b>学术标准</b>: 适合论文发表</p>
        <p>• <b>多彩模式</b>: 丰富的颜色区分</p>
        <p>• <b>单色模式</b>: 灰度显示</p>
        <h3>性能优化</h3>
        <p>• 调整最大点数限制</p>
        <p>• 启用多核处理和缓存机制</p>
        <p>• 使用权重阈值过滤数据</p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("使用说明")
        msg.setText(usage_text)
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_shortcuts(self):
        shortcuts_text = """
        <h2>快捷键列表</h2>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>快捷键</th><th>功能</th></tr>
        <tr><td><b>Ctrl+O</b></td><td>打开文件</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>退出程序</td></tr>
        <tr><td><b>Ctrl+1</b></td><td>完整能带结构</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>费米面专注模式</td></tr>
        <tr><td><b>Ctrl+A</b></td><td>全选轨道</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>全不选轨道</td></tr>
        <tr><td><b>Ctrl+I</b></td><td>反选轨道</td></tr>
        <tr><td><b>Ctrl+R</b></td><td>重置缩放</td></tr>
        <tr><td><b>F5</b></td><td>刷新图形</td></tr>
        <tr><td><b>F1</b></td><td>使用说明</td></tr>
        <tr><td><b>Ctrl+P</b></td><td>切换控制面板</td></tr>
        <tr><td><b>Ctrl+L</b></td><td>切换日志区域</td></tr>
        <tr><td><b>Shift+拖拽</b></td><td>框选放大</td></tr>
        </table>
        <p><i>提示: 鼠标悬停在菜单项上可查看详细说明</i></p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("快捷键")
        msg.setText(shortcuts_text)
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def show_about_dialog(self):
        about_text = """
        <h2>FPLO能带权重可视化工具</h2>
        <p><b>版本:</b> 2.0.0 (性能优化版)</p>
        <p><b>开发:</b> 中国科学技术大学</p>
        <h3>主要功能</h3>
        <ul>
        <li>交互式FPLO能带结构可视化</li>
        <li>轨道权重投影分析</li>
        <li>费米面专注模式</li>
        <li>框选放大功能</li>
        <li>多种颜色方案</li>
        <li>多核处理优化</li>
        <li>高质量图像导出</li>
        </ul>
        <h3>支持格式</h3>
        <p>输入: FPLO +bweight文件</p>
        <p>输出: PNG, PDF, SVG格式</p>
        <h3>技术栈</h3>
        <p>Python 3.7+ • PyQt5 • Matplotlib • NumPy • SciPy</p>
        <p><i>感谢使用FPLO可视化工具！</i></p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("关于程序")
        msg.setText(about_text)
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def export_image(self, format_type=None):
        """导出图像"""
        if not self.plot_widget.visualizer:
            QMessageBox.warning(self, "警告", "请先加载数据文件")
            return
        if format_type == 'png':
            filter_str = "PNG文件 (*.png)"; default_ext = ".png"
        elif format_type == 'pdf':
            filter_str = "PDF文件 (*.pdf)"; default_ext = ".pdf"
        elif format_type == 'svg':
            filter_str = "SVG文件 (*.svg)"; default_ext = ".svg"
        elif format_type == 'eps':
            filter_str = "EPS文件 (*.eps)"; default_ext = ".eps"
        else:
            filter_str = "PNG文件 (*.png);;PDF文件 (*.pdf);;SVG文件 (*.svg);;EPS文件 (*.eps)"; default_ext = ".png"
        view_mode = self.plot_widget.current_plot_type
        default_name = f"fplo_band_structure_{view_mode}{default_ext}"
        filename, _ = QFileDialog.getSaveFileName(self, "保存图像", default_name, filter_str)
        if filename:
            try:
                dpi = self.plot_widget.plot_settings.get('figure_dpi', 150)
                self.plot_widget.figure.savefig(
                    filename, dpi=dpi, bbox_inches='tight', facecolor='white',
                    edgecolor='none', transparent=False
                )
                self.log_widget.log_info(f"图像已保存: {filename} (DPI: {dpi})")
                QMessageBox.information(self, "成功", f"图像导出成功!\n文件: {filename}")
            except Exception as e:
                self.log_widget.log_error(f"图像导出失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"图像导出失败:\n{str(e)}")

    def export_image_with_quality(self, format_type, quality):
        """导出指定清晰度的图像"""
        if not hasattr(self.plot_widget, 'figure') or self.plot_widget.figure is None:
            QMessageBox.warning(self, "警告", "没有可导出的图形")
            return
        quality_settings = {
            'standard': {'dpi': 150, 'desc': '标准清晰度'},
            'high': {'dpi': 300, 'desc': '高清晰度'},
            'ultra': {'dpi': 600, 'desc': '超高清晰度'}
        }
        if quality not in quality_settings:
            quality = 'standard'
        dpi = quality_settings[quality]['dpi']
        desc = quality_settings[quality]['desc']
        if format_type == 'png':
            filter_str = "PNG图像 (*.png)"; default_ext = ".png"
        else:
            self.export_image(format_type); return
        view_mode = self.plot_widget.current_plot_type
        default_name = f"fplo_band_structure_{view_mode}_{quality}{default_ext}"
        filename, _ = QFileDialog.getSaveFileName(self, f"导出{desc}图像", default_name, filter_str)
        if filename:
            try:
                self.plot_widget.figure.savefig(
                    filename, dpi=dpi, bbox_inches='tight', facecolor='white',
                    edgecolor='none', format=format_type, transparent=False
                )
                self.log_widget.log_info(f"图像已导出: {filename} ({desc}, {dpi} DPI)")
                QMessageBox.information(self, "导出成功",
                                      f"图像已成功导出为 {desc}\n"
                                      f"文件: {filename}\n"
                                      f"分辨率: {dpi} DPI")
            except Exception as e:
                self.log_widget.log_error(f"导出图像失败: {str(e)}")
                QMessageBox.critical(self, "导出失败", f"导出图像时发生错误:\n{str(e)}")
