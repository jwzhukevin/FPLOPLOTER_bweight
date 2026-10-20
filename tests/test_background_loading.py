"""Exercise real QThreads and queued Qt delivery, including deliberately late results."""

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PyQt5 import sip
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from orbital_data import AnalysisCancelled
from fplo_fermi_visualizer import FPLOFermiVisualizer
from fplo_visualizer import FPLOVisualizer
from fplo_gui_main import InteractivePlotWidget
from gui.loading import BackgroundLoader
from gui.main_window import MainWindow
from gui.tools import DataLoaderThread


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def until(predicate, timeout=5000):
    deadline = time.monotonic() + timeout / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(5)
    assert predicate(), 'Qt task did not reach expected state'


@pytest.fixture
def gates(monkeypatch, app):
    workers = []
    owners = []

    class GateWorker(QThread):
        result = pyqtSignal(object)
        error = pyqtSignal(str)
        status = pyqtSignal(str)

        def __init__(self, filename, mode, parent):
            super().__init__(parent)
            owner = parent
            while owner is not None:
                owners.append(owner)
                owner = owner.parent()
            self.filename, self.mode = filename, mode
            self.generation = 0
            self.entered = threading.Event()
            self.release = threading.Event()
            workers.append(self)

        def run(self):
            self.entered.set()
            self.release.wait(5)
            # Intentionally emit even after interruption to reproduce queued-result races.
            self.status.emit('late status')
            if self.filename == 'bad':
                self.error.emit('late error')
            elif Path(self.filename).is_file():
                if self.mode == 'fermi':
                    obj = FPLOFermiVisualizer(self.filename, configure_plot=False)
                else:
                    obj = FPLOVisualizer(self.filename, configure_plot=False)
                    obj.parse_header_and_system()
                    obj.read_and_parse_data(max_kpoints=200)
                self.result.emit(obj)
            else:
                self.result.emit(SimpleNamespace(filename=self.filename))

    monkeypatch.setattr('gui.loading.DataLoaderThread', GateWorker)
    yield workers
    # An assertion may stop a test with a replacement still pending. Prevent
    # teardown from starting another worker after the initial release loop.
    for owner in owners:
        if isinstance(owner, BackgroundLoader) and not sip.isdeleted(owner):
            owner.shutdown()
    for worker in workers:
        worker.release.set()
    for worker in workers:
        if not sip.isdeleted(worker):
            assert worker.wait(5000)
    app.processEvents()
    owners.clear()


def test_latest_request_only_and_one_running_worker(app, gates):
    loader = BackgroundLoader()
    results, statuses = [], []
    loader.result.connect(lambda obj: results.append(obj.filename))
    loader.status.connect(statuses.append)
    loader.request('A', 'fermi')
    until(gates[0].entered.is_set)
    loader.request('B', 'fermi')
    loader.request('C', 'fermi')
    assert len(gates) == 1
    assert gates[0].isInterruptionRequested()
    gates[0].release.set()
    until(lambda: len(gates) == 2)
    assert gates[1].filename == 'C'
    assert results == [] and statuses == []
    gates[1].release.set()
    until(lambda: not loader.busy)
    assert results == ['C']


def test_cancel_suppresses_late_error_and_allows_retry(app, gates):
    loader = BackgroundLoader()
    errors, results = [], []
    loader.error.connect(errors.append)
    loader.result.connect(results.append)
    loader.request('bad', 'fermi')
    until(gates[0].entered.is_set)
    loader.cancel()
    gates[0].release.set()
    until(lambda: not loader.busy)
    assert errors == [] and results == []
    loader.request('retry', 'fermi')
    gates[1].release.set()
    until(lambda: not loader.busy)
    assert results[0].filename == 'retry'


def test_shutdown_retains_worker_until_finished_and_rejects_new_requests(app, gates):
    loader = BackgroundLoader()
    results = []
    loader.result.connect(results.append)
    loader.request('A', 'fermi')
    until(gates[0].entered.is_set)
    loader.shutdown()
    loader.request('B', 'fermi')
    assert loader.busy and loader._worker is gates[0]
    gates[0].release.set()
    until(lambda: not loader.busy)
    assert results == [] and len(gates) == 1


def test_first_fermi_load_keeps_qt_alive_and_uses_latest_settings(app, gates, weight_file, monkeypatch):
    widget = InteractivePlotWidget()
    widget.current_filename = str(weight_file)
    draws = []
    monkeypatch.setattr(widget, 'plot_current_view', lambda: draws.append(QThread.currentThread()))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(2)
    widget.set_view_mode('fermi')
    until(gates[0].entered.is_set)
    QTest.qWait(40)
    assert len(ticks) >= 2 and draws == []
    widget.plot_settings['fermi_window'] = [-2., 2.]
    widget.plot_settings['point_alpha'] = .3
    # A duplicate mode signal must not restart the same load.
    widget.set_view_mode('fermi')
    assert len(gates) == 1
    gates[0].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert widget.visualizer.energy_window == (-2, 2)
    assert widget.visualizer.plot_settings['point_alpha'] == .3
    assert draws == [app.thread()]
    timer.stop()
    widget.close()


def test_mode_switch_back_and_file_change_discard_old_fermi_result(app, gates, weight_file, monkeypatch):
    widget = InteractivePlotWidget()
    monkeypatch.setattr(widget, 'plot_current_view', lambda: None)
    original = SimpleNamespace(filename='old')
    widget.complete_visualizer = widget.visualizer = original
    widget.current_filename = str(weight_file)
    widget.set_view_mode('fermi')
    until(gates[0].entered.is_set)
    widget.set_view_mode('complete')
    gates[0].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert widget.visualizer is original
    assert getattr(widget, 'fermi_visualizer', None) is None
    widget.set_view_mode('fermi')
    until(gates[1].entered.is_set)
    widget.begin_file_change()
    gates[1].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert widget.visualizer is None and widget.fermi_visualizer is None
    widget.close()


def test_close_widget_is_deferred_without_blocking(app, gates):
    widget = InteractivePlotWidget()
    widget.show()
    widget.current_filename = 'A'
    widget.set_view_mode('fermi')
    until(gates[0].entered.is_set)
    assert not widget.close()
    assert widget._close_pending and widget._fermi_loader.busy
    gates[0].release.set()
    until(lambda: not widget.isVisible())
    assert not widget._fermi_loader.busy


def test_fermi_error_restores_complete_view_and_retry_succeeds(app, gates, weight_file, monkeypatch):
    widget = InteractivePlotWidget()
    monkeypatch.setattr(widget, 'plot_current_view', lambda: None)
    original = SimpleNamespace(filename='original')
    widget.visualizer = widget.complete_visualizer = original
    widget.current_filename = 'bad'
    statuses = []
    widget.loading_status.connect(statuses.append)
    widget.set_view_mode('fermi')
    gates[0].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert widget.current_plot_type == 'complete' and widget.visualizer is original
    assert any('late error' in message for message in statuses)
    widget.current_filename = str(weight_file)
    widget.set_view_mode('fermi')
    gates[1].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert isinstance(widget.visualizer, FPLOFermiVisualizer)
    widget.close()


def test_invalid_window_changed_during_load_is_reported_without_slot_exception(app, gates, weight_file, monkeypatch):
    widget = InteractivePlotWidget()
    monkeypatch.setattr(widget, 'plot_current_view', lambda: None)
    original = SimpleNamespace(filename='original')
    widget.visualizer = widget.complete_visualizer = original
    widget.current_filename = str(weight_file)
    statuses = []
    widget.loading_status.connect(statuses.append)
    widget.set_view_mode('fermi')
    widget.plot_settings['fermi_window'] = [0., 0.]
    gates[0].release.set()
    until(lambda: not widget._fermi_loader.busy)
    assert widget.current_plot_type == 'complete' and widget.visualizer is original
    assert widget.fermi_visualizer is None
    assert any('positive' in message for message in statuses)
    widget.close()


def test_main_window_close_waits_for_both_loaders(app, gates, monkeypatch):
    monkeypatch.setattr('gui.main_window.logger.finalize_log', lambda: None)
    window = MainWindow()
    window.show()
    window.load_file('A')
    window.plot_widget.current_filename = 'old'
    window.plot_widget.set_view_mode('fermi')
    until(lambda: len(gates) == 2 and all(w.entered.is_set() for w in gates))
    assert not window.close()
    assert window._closing and window.isVisible()
    assert all(worker.isInterruptionRequested() for worker in gates)
    gates[0].release.set()
    until(lambda: not window._load_controller.busy)
    assert window.isVisible()
    gates[1].release.set()
    until(lambda: not window.isVisible())
    assert not window.plot_widget._fermi_loader.busy


def test_main_window_switches_file_and_cancel_button_invalidates_results(app, gates, weight_file, monkeypatch):
    monkeypatch.setattr('gui.main_window.logger.finalize_log', lambda: None)
    window = MainWindow()
    window.load_file('old')
    until(gates[0].entered.is_set)
    window.load_file(str(weight_file))
    gates[0].release.set()
    until(lambda: len(gates) == 2)
    gates[1].release.set()
    until(lambda: not window._load_controller.busy)
    assert window.plot_widget.current_filename == str(weight_file)
    window.plot_widget.set_view_mode('fermi')
    until(lambda: len(gates) == 3 and gates[2].entered.is_set())
    window.cancel_load_button.click()
    gates[2].release.set()
    until(lambda: not window.plot_widget._fermi_loader.busy)
    assert window.plot_widget.current_plot_type == 'complete'
    assert window.plot_widget.fermi_visualizer is None
    window.close()


def test_real_worker_matches_synchronous_analysis_without_plot_setup(app, weight_file, monkeypatch):
    reference = FPLOFermiVisualizer(str(weight_file), configure_plot=False)
    setup_threads = []
    monkeypatch.setattr(FPLOFermiVisualizer, '_setup_matplotlib', lambda _: setup_threads.append(QThread.currentThread()))
    loader = BackgroundLoader()
    results = []
    loader.result.connect(results.append)
    loader.request(str(weight_file), 'fermi')
    until(lambda: not loader.busy)
    assert len(results) == 1 and setup_threads == []
    obj = results[0]
    np.testing.assert_array_equal(obj.band_energies, reference.band_energies)
    np.testing.assert_array_equal(obj.band_weights, reference.band_weights)
    assert obj.energy_window == reference.energy_window
    assert obj.important_bands == reference.important_bands
    assert obj._cancel_check is None


def test_real_worker_reports_failure(app, weight_file):
    loader = BackgroundLoader()
    errors = []
    loader.error.connect(errors.append)
    loader.request(str(weight_file.parent / 'missing'), 'fermi')
    until(lambda: not loader.busy)
    assert len(errors) == 1


def test_real_complete_worker_matches_reader(app, weight_file):
    reference = FPLOVisualizer(str(weight_file), configure_plot=False)
    reference.parse_header_and_system()
    reference.read_and_parse_data(max_kpoints=200)
    loader = BackgroundLoader()
    results = []
    loader.result.connect(results.append)
    loader.request(str(weight_file), 'complete')
    until(lambda: not loader.busy)
    assert len(results) == 1
    np.testing.assert_array_equal(results[0].band_weights, reference.band_weights)
    np.testing.assert_array_equal(results[0].k_points, reference.k_points)
    assert results[0]._cancel_check is None


def test_worker_already_interrupted_does_not_start(monkeypatch):
    worker = DataLoaderThread('missing', 'fermi')
    monkeypatch.setattr(worker, 'isInterruptionRequested', lambda: True)
    errors = []
    worker.error.connect(errors.append)
    worker.run()
    assert errors == []


@pytest.mark.parametrize('exception', [AnalysisCancelled, RuntimeError])
def test_real_worker_cancellation_is_silent(app, weight_file, monkeypatch, exception):
    entered, release = threading.Event(), threading.Event()

    def blocked_analysis(obj, *args, **kwargs):
        entered.set()
        release.wait(3)
        raise exception('cancelled during analysis')

    monkeypatch.setattr(FPLOFermiVisualizer, 'read_and_parse_data', blocked_analysis)
    loader = BackgroundLoader()
    results, errors = [], []
    loader.result.connect(results.append)
    loader.error.connect(errors.append)
    loader.request(str(weight_file), 'fermi')
    until(entered.is_set)
    loader.cancel()
    release.set()
    until(lambda: not loader.busy)
    assert results == [] and errors == []


def test_cancel_during_real_file_read(weight_file):
    calls = []

    def cancelled():
        calls.append(1)
        return len(calls) > 3

    with pytest.raises(AnalysisCancelled):
        FPLOFermiVisualizer(str(weight_file), cancel_check=cancelled, configure_plot=False)


def test_cancel_during_weight_density_analysis():
    obj = FPLOFermiVisualizer.__new__(FPLOFermiVisualizer)
    obj.band_energies = np.array([[-1., 1.], [-.5, .5]])
    obj.num_kpoints, obj.num_bands = 2, 2
    obj.weights_data = np.ones((2, 2, 1))
    checks = []

    def cancelled():
        checks.append(1)
        return len(checks) > 3

    obj._cancel_check = cancelled
    with pytest.raises(AnalysisCancelled):
        obj._calculate_orbital_weight_density()
    assert len(checks) == 4
