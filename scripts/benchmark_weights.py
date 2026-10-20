"""Compare HEAD's original renderer with the working tree on identical data.

Run from the repository root with numpy, matplotlib and PyQt5 available:
    python scripts/benchmark_weights.py --data +bweights --repeats 5
The baseline is read from Git; neither input nor Git state is modified.
"""

import argparse
import ast
import contextlib
import io
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from fplo_visualizer import FPLOVisualizer
from fplo_gui_main import InteractivePlotWidget


def baseline_renderer(ref):
    text = subprocess.check_output(['git', 'show', f'{ref}:fplo_gui_main.py'], encoding='utf-8')
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == 'InteractivePlotWidget')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_plot_orbital_weights_singlecore')
    namespace = {'np': np}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<HEAD baseline>', 'exec'), namespace)
    return namespace[method.name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='+bweights')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--baseline-ref', default='HEAD', help='Pre-change Git revision')
    parser.add_argument('--output', type=Path, help='Optional JSON evidence file')
    parser.add_argument('--preview-dir', type=Path, help='Optional before/after PNG directory')
    args = parser.parse_args()
    visualizer = FPLOVisualizer(args.data)
    visualizer.parse_header_and_system()
    # Match the existing GUI's sampling exactly; no new sampling rule is applied.
    raw = np.loadtxt(args.data)
    nb = next(i for i, row in enumerate(raw) if abs(row[0]) >= 1e-6)
    nk = len(raw) // nb
    shaped = raw.reshape(nk, nb, -1)[::max(1, nk // 200)]
    visualizer.k_points = shaped[:, 0, 0]
    visualizer.band_energies = shaped[:, :, 1]
    visualizer.band_weights = shaped[:, :, 2:]
    visualizer.num_bands = nb
    harness = SimpleNamespace(visualizer=visualizer, visible_orbitals={})
    functions = {'baseline': baseline_renderer(args.baseline_ref), 'optimized': InteractivePlotWidget._plot_orbital_weights_singlecore}
    input_hash = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
    report = {'baseline_ref': subprocess.check_output(['git', 'rev-parse', args.baseline_ref], text=True).strip(),
              'input_sha256': input_hash, 'shape': list(shaped.shape), 'groups': len(visualizer.orbital_info), 'window': [-5, 5],
              'threshold': .02, 'repeats': args.repeats, 'runs': {}}
    rendered_points = {}
    rendered_pixels = {}
    for name, function in functions.items():
        timings = []
        # Warm fonts and the optimized sum cache before measuring repeat redraws.
        for repeat in range(args.repeats + 1):
            fig = Figure(figsize=(10, 6), dpi=100)
            canvas = FigureCanvasAgg(fig)
            ax = fig.add_subplot()
            ax.set_xlim(visualizer.k_points.min(), visualizer.k_points.max())
            ax.set_ylim(-5, 5)
            start = time.perf_counter()
            with contextlib.redirect_stdout(io.StringIO()):
                function(harness, ax, [-5, 5], .02, 1., .7, 2., 50., 1000)
            prepared = time.perf_counter()
            canvas.draw()
            finished = time.perf_counter()
            if repeat:
                timings.append([(prepared - start) * 1000, (finished - prepared) * 1000])
        report['runs'][name] = {'median_prepare_ms': float(np.median(timings, axis=0)[0]),
                                'median_draw_ms': float(np.median(timings, axis=0)[1]),
                                'collections': len(ax.collections),
                                'points': sum(len(c.get_offsets()) for c in ax.collections)}
        rendered_points[name] = (
            np.concatenate([c.get_offsets() for c in ax.collections]),
            np.concatenate([c.get_sizes() for c in ax.collections]),
        )
        rendered_pixels[name] = np.asarray(canvas.buffer_rgba()).copy()
        if args.preview_dir:
            args.preview_dir.mkdir(parents=True, exist_ok=True)
            fig.savefig(args.preview_dir / f'{name}.png', dpi=100)
    for baseline, optimized in zip(rendered_points['baseline'], rendered_points['optimized']):
        np.testing.assert_allclose(baseline, optimized, rtol=1e-12, atol=1e-12)
    report['point_positions_and_sizes_match'] = True
    delta = np.abs(rendered_pixels['baseline'].astype(int) - rendered_pixels['optimized'].astype(int))
    report['render_pixel_mean_absolute_difference'] = float(delta.mean())
    report['input_unchanged'] = hashlib.sha256(Path(args.data).read_bytes()).hexdigest() == input_hash
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
