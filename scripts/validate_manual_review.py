"""Validate full local weight fixtures and render the actual Qt inspection UI.

Run with the project's NumPy/Qt/Matplotlib environment and QT_QPA_PLATFORM=offscreen.
Outputs go to an explicit evidence directory; FPLO inputs are never modified.
"""

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fplo_visualizer import FPLOVisualizer
from orbital_data import grouped_weights


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    paths = [p for p in [ROOT / '+bweights', *sorted(ROOT.glob('*/+bweights'))] if p.is_file()]
    if not paths:
        raise RuntimeError('No real FPLO fixtures found')
    sources = ['orbital_data.py', 'weight_plot.py', 'fplo_visualizer.py',
               'fplo_fermi_visualizer.py', 'fplo_gui_main.py', 'gui/tools.py']
    source_hashes = {name: sha256(ROOT / name) for name in sources}
    report = {'inputs': [], 'rendered_files': [], 'source_sha256': source_hashes,
              'python': sys.version, 'numpy': np.__version__}
    for path in paths:
        before = sha256(path)
        started = time.perf_counter()
        obj = FPLOVisualizer(str(path), configure_plot=False)
        obj.parse_header_and_system()
        obj.read_and_parse_data(max_kpoints=200)
        elapsed = time.perf_counter() - started
        # Independent parser for all energy and coordinate fields, not sampled rows.
        reference = np.loadtxt(path, usecols=(0, 1)).reshape(obj.num_kpoints, obj.num_bands, 2)
        np.testing.assert_array_equal(obj.k_points, reference[:, 0, 0])
        np.testing.assert_array_equal(obj.band_energies, reference[:, :, 1])
        totals = sum(grouped_weights(obj, key) for key in obj.orbital_info)
        np.testing.assert_allclose(totals, obj.band_weights.sum(axis=2), rtol=1e-12, atol=1e-12)
        assert before == sha256(path), 'Raw input changed during validation'
        report['inputs'].append(dict(
            file=str(path.relative_to(ROOT)), sha256=before, full_shape=list(obj.band_weights.shape),
            site_shells=len(obj.orbital_info), display_limit=obj.plot_max_kpoints,
            load_seconds=round(elapsed, 3), full_energies_match=True, group_sums_match=True,
            input_unchanged=True))
        print('VALIDATED', path.name, obj.band_weights.shape, flush=True)
        del obj, reference, totals
        gc.collect()

    from PyQt5.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    path = paths[0]
    obj = FPLOVisualizer(str(path))
    obj.parse_header_and_system()
    obj.read_and_parse_data()
    window.current_filename = str(path)
    window.on_data_loaded(obj)
    window.resize(1600, 1000)
    window.show()
    app.processEvents()
    plot = window.plot_widget
    near = np.abs(obj.band_energies) <= 2
    ranked = sorted(obj.orbital_info, key=lambda key: grouped_weights(obj, key)[near].sum(), reverse=True)
    for key in ranked[:4]:
        window.control_panel.orbital_checkboxes[key].setChecked(True)
    app.processEvents()
    plot.zoom_to_region(float(obj.k_points.min()), float(obj.k_points.max()), -2, 2)
    app.processEvents()
    screenshot = args.output / 'manual-review-window.png'
    assert window.grab().save(str(screenshot))
    assert np.asarray(plot.canvas.buffer_rgba()).std() > 0
    for suffix in ('png', 'pdf', 'svg'):
        target = args.output / f'manual-review-bands.{suffix}'
        plot.figure.savefig(target, dpi=120, bbox_inches='tight')
        assert target.stat().st_size > 1000
        report['rendered_files'].append(target.name)
    report['rendered_files'].append(screenshot.name)
    report['selected_site_shells'] = ranked[:4]
    report['qt_platform'] = app.platformName()
    assert source_hashes == {name: sha256(ROOT / name) for name in sources}, 'Sources changed during validation'
    window.close()
    app.processEvents()
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
