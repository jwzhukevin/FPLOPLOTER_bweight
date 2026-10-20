"""Run targeted mutations in disposable copies; never edit live sources."""

import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['orbital_data.py', 'weight_plot.py', 'fplo_visualizer.py', 'fplo_fermi_visualizer.py',
           'fplo_gui_main.py', 'log_manager.py', 'performance_monitor.py',
           'gui/tools.py', 'gui/log_widget.py', 'gui/main_window.py', 'gui/loading.py']
MUTATIONS = [
    ('repeat_header', 'fplo_fermi_visualizer.py', '        self.orbital_info = groups',
     '        for key, indices in groups.items():\n            self.orbital_info.setdefault(key, []).extend(indices)'),
    ('unknown_column_shift', 'orbital_data.py',
     "            raise ValueError(f'Unrecognized orbital label at weight column {len(columns)}: {label!r}')",
     '            continue'),
    ('miss_window_crossing', 'orbital_data.py', '        inside |= np.any(crossing, axis=0)', '        pass'),
    ('metal_false_gap', 'fplo_fermi_visualizer.py',
     '        band_gap = 0.0 if crosses_fermi else cbm - vbm', '        band_gap = cbm - vbm'),
    ('upper_boundary_overflow', 'fplo_fermi_visualizer.py',
     '        best_boundary_idx = min(len(energy_grid) - 1, fermi_idx + base_idx_half)',
     '        best_boundary_idx = fermi_idx + base_idx_half'),
    ('wrong_group_sum', 'orbital_data.py', '.sum(axis=2)', '.mean(axis=2)'),
    ('ignore_window_in_worker', 'gui/tools.py', "settings.get('energy_range')", 'None'),
    ('change_point_normalization', 'orbital_data.py', 'np.asarray(weights) * (max_size - min_size)',
     'np.asarray(weights) / np.max(weights) * (max_size - min_size)'),
    ('duplicate_redraw', 'fplo_gui_main.py',
     '        # Canvas is drawn once by plot_current_view().', '        self.canvas.draw()'),
    ('accept_stale_generation', 'gui/loading.py', 'sender.generation == self._generation', 'True'),
    ('no_thread_interruption', 'gui/loading.py', '            self._worker.requestInterruption()', '            pass'),
    ('ignore_numerical_cancellation', 'orbital_data.py',
     '    if check is not None and check():', '    if False:'),
    ('merge_atomic_sites', 'orbital_data.py',
     '''key = f"{column['element']}({column['site']})_{column['shell']}"''',
     '''key = f"{column['element']}_{column['shell']}"'''),
    ('accept_nonfinite_input', 'orbital_data.py', '        if not np.isfinite(row).all():',
     '        if False:'),
    ('accept_truncated_input', 'orbital_data.py',
     '    if count != len(data):', '    if False:'),
    ('ignore_block_coordinate', 'orbital_data.py',
     '    if not np.all(data[:, :, 0] == data[:, :1, 0]):', '    if False:'),
    ('discard_full_resolution', 'fplo_visualizer.py',
     '        self.k_points = k_points\n        self.band_energies = energies\n        self.band_weights = weights',
     '        self.k_points = k_points[::2]\n        self.band_energies = energies[::2]\n        self.band_weights = weights[::2]'),
    ('ignore_zoom_viewport', 'orbital_data.py', '    if k_range is not None:', '    if False:'),
    ('drop_display_endpoint', 'orbital_data.py',
     'np.linspace(0, len(weight) - 1, int(max_points), dtype=int)',
     'np.arange(int(max_points))'),
]


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['all', 'threading', 'manual-review'], default='all')
    args = parser.parse_args()
    selected = MUTATIONS
    if args.scope == 'threading':
        selected = [m for m in MUTATIONS if m[0] in {
            'accept_stale_generation', 'no_thread_interruption', 'ignore_numerical_cancellation'}]
    elif args.scope == 'manual-review':
        selected = [m for m in MUTATIONS if m[0] in {
            'merge_atomic_sites', 'change_point_normalization', 'accept_nonfinite_input',
            'accept_truncated_input', 'ignore_block_coordinate', 'discard_full_resolution',
            'ignore_zoom_viewport', 'drop_display_endpoint'}]
    before = source_hashes()
    artifacts = ROOT / '.test-artifacts'
    artifacts.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='weight-mutations-', dir=artifacts))
    results = []
    for name, filename, old, new in selected:
        target = scratch / name
        target.mkdir()
        for source in SOURCES:
            destination = target / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / source, destination)
        shutil.copytree(ROOT / 'tests', target / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
        path = target / filename
        text = path.read_text(encoding='utf-8')
        if old not in text:
            raise RuntimeError(f'Mutation anchor not found: {name}')
        path.write_text(text.replace(old, new, 1), encoding='utf-8')
        # A killed GUI mutation need not exercise additional lifecycle paths in
        # the already-broken process; runner/import errors still are not kills.
        code = 'import sys,pytest; sys.path.insert(0, "."); raise SystemExit(pytest.main(["tests", "-q", "-x", "-p", "no:cacheprovider"]))'
        process = subprocess.run([sys.executable, '-B', '-c', code], cwd=target,
                                 capture_output=True, text=True, timeout=90)
        (target / 'pytest-output.txt').write_text(process.stdout + process.stderr, encoding='utf-8')
        # pytest 1 means assertions failed; collection/import/runner errors are not kills.
        status = {0: 'survived', 1: 'killed'}.get(process.returncode, 'runner_error')
        results.append({'name': name, 'status': status, 'exit_code': process.returncode})
        print(name, status, flush=True)
    report = {'mutations': results, 'live_sources_unchanged': source_hashes() == before,
              'scratch': str(scratch)}
    report_name = {'threading': 'thread-mutation-report.json',
                   'manual-review': 'manual-review-mutation-report.json'}.get(args.scope, 'mutation-report.json')
    (artifacts / report_name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if not report['live_sources_unchanged'] or any(r['status'] != 'killed' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
