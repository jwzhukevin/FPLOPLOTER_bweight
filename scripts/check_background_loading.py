"""Measure Qt heartbeat and cooperative cancellation on an actual input file."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from fplo_gui_main import InteractivePlotWidget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='+bweights')
    parser.add_argument('--output', type=Path, default=Path('.test-artifacts/background-wsl.json'))
    args = parser.parse_args()
    path = Path(args.data).resolve()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    app = QApplication.instance() or QApplication([])
    widget = InteractivePlotWidget()
    widget.current_filename = str(path)
    ticks = []
    report = {'input_sha256': before, 'cancelled': False}
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: ticks.append(time.perf_counter()))
    heartbeat.start(10)
    started = time.perf_counter()

    def cancel():
        report['cancelled'] = True
        report['cancel_requested_at'] = time.perf_counter()
        widget.cancel_fermi_load()

    def completed():
        report['stopped_at'] = time.perf_counter()
        heartbeat.stop()
        app.quit()

    widget.loading_idle.connect(completed)
    widget.set_view_mode('fermi')
    report['dispatch_ms'] = (time.perf_counter() - started) * 1000
    QTimer.singleShot(250, cancel)
    app.exec_()
    report['heartbeat_ticks'] = len(ticks)
    # Include the period before the first tick and after the last tick.
    timestamps = [started, *ticks, report['stopped_at']]
    report['max_event_loop_gap_ms'] = max(b - a for a, b in zip(timestamps, timestamps[1:])) * 1000
    if report['cancelled']:
        report['cancel_to_idle_ms'] = (report['stopped_at'] - report['cancel_requested_at']) * 1000
    report.pop('cancel_requested_at', None)
    report.pop('stopped_at')
    report['worker_stopped'] = not widget._fermi_loader.busy
    report['no_fermi_result_applied'] = getattr(widget, 'fermi_visualizer', None) is None
    report['input_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == before
    widget.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not all(report[key] for key in ['cancelled', 'worker_stopped', 'no_fermi_result_applied', 'input_unchanged']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
