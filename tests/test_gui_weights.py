from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

from fplo_gui_main import ControlPanel, InteractivePlotWidget
from fplo_visualizer import FPLOVisualizer
from gui.tools import process_single_orbital


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(app):
    result = InteractivePlotWidget()
    yield result
    result._redraw_timer.stop()
    result.close()


class RecordingAxes:
    def __init__(self):
        self.points = []

    def scatter(self, x, y, **kwargs):
        self.points.append((np.array(x), np.array(y), kwargs))


def test_batch_uses_shared_raw_weight_scale_and_visibility(widget):
    widget.visualizer = SimpleNamespace(
        k_points=np.array([0., 1., 2.]),
        band_energies=np.array([[-10., -1.], [0., 0.], [1., 1.]]),
        band_weights=np.array([[[.9, .1], [.2, .8]], [[.1, .9], [.4, .6]], [[.2, .8], [.1, .9]]]),
        orbital_info={'Cs_5s': [0], 'Ag_4d': [1]},
        orbital_colors={'Cs_5s': 'red', 'Ag_4d': 'blue'}, num_bands=2,
    )
    widget.visible_orbitals = {'Cs_5s': True, 'Ag_4d': False}
    ax = RecordingAxes()
    widget._plot_orbital_weights_singlecore(ax, [-1, 1], .02, 1, .7, 2, 50, 10)
    assert len(ax.points) == 1
    k, energy, style = ax.points[0]
    np.testing.assert_array_equal(k, [1, 2, 0, 1, 2])
    np.testing.assert_array_equal(energy, [0, 1, -1, 0, 1])
    np.testing.assert_allclose(style['s'], [6.8, 11.6, 11.6, 21.2, 6.8])
    assert style['c'] == 'red'
    other = RecordingAxes()
    widget._plot_orbital_weights_multicore(other, [-1, 1], .02, 1, .7, 2, 50, 10)
    np.testing.assert_array_equal(other.points[0][1], energy)
    np.testing.assert_array_equal(other.points[0][2]['s'], style['s'])


def test_worker_filters_window_before_limiting_points():
    result = process_single_orbital(('Cs_5s', np.arange(3), np.array([-10., 0., 1.]),
                                    np.array([.9, .1, .2]),
                                    {'energy_range': [-1, 1], 'max_points_per_orbital': 1}))
    np.testing.assert_array_equal(result['energies'], [1.])


def test_burst_of_ui_changes_draws_once(widget, app, monkeypatch):
    widget.visualizer = SimpleNamespace()
    # A completed plot now records its viewport; keep that real renderer contract
    # while isolating signal coalescing from expensive artist construction.
    widget.figure.add_subplot(111)
    monkeypatch.setattr(widget, 'plot_complete_structure', Mock())
    draw = Mock()
    monkeypatch.setattr(widget.canvas, 'draw', draw)
    monkeypatch.setattr(widget.canvas, 'flush_events', lambda: None)
    widget.update_plot_settings({'point_alpha': .5})
    widget.update_plot_settings({'title': 'updated'})
    widget.toggle_orbital_visibility('Cs_5s', True)
    assert draw.call_count == 0
    app.processEvents()
    assert draw.call_count == 1


@pytest.mark.parametrize('mode', ['complete', 'fermi'])
def test_real_plot_draws_once_and_renders_offscreen(widget, weight_file, monkeypatch, mode):
    visualizer = FPLOVisualizer(str(weight_file))
    visualizer.parse_header_and_system()
    visualizer.read_and_parse_data()
    widget.visualizer = visualizer
    widget.visible_orbitals = {key: True for key in visualizer.orbital_info}
    widget.current_plot_type = mode
    original_draw = widget.canvas.draw
    draw = Mock(wraps=original_draw)
    monkeypatch.setattr(widget.canvas, 'draw', draw)
    widget.plot_current_view()
    assert draw.call_count == 1
    assert len(widget.figure.axes[0].collections) == 2
    pixels = np.asarray(widget.canvas.buffer_rgba())
    assert pixels.shape[0] > 0 and pixels.std() > 0


def test_loading_another_file_discards_previous_fermi_visualizer(widget, weight_file, monkeypatch):
    obj = FPLOVisualizer(str(weight_file))
    obj.parse_header_and_system()
    obj.read_and_parse_data()
    widget.fermi_visualizer = object()
    widget.visible_orbitals = {'stale': True}
    monkeypatch.setattr(widget, 'plot_current_view', lambda: None)
    widget.set_visualizer(obj, str(weight_file))
    assert widget.fermi_visualizer is None
    assert 'stale' not in widget.visible_orbitals
    assert widget.complete_visualizer is obj


def test_control_panel_emits_weight_settings_without_worker_toggle(app):
    panel = ControlPanel()
    settings = []
    panel.settings_changed.connect(settings.append)
    panel.on_orbital_settings_changed()
    assert settings[-1]['weight_threshold'] == panel.weight_threshold_spin.value()
    assert settings[-1]['max_points_per_orbital'] == panel.max_points_spin.value()
    assert 'use_multiprocessing' not in settings[-1]
    panel.close()


@pytest.mark.parametrize('mode', ['complete', 'fermi'])
def test_zoom_recovers_unsampled_state_from_full_data(widget, tmp_path, mode):
    path = tmp_path / '+bweights'
    rows = [f'{k} 0 {0.8 if k == 5 else 0.03} {0.2 if k == 5 else 0.97}' for k in range(11)]
    path.write_text('# 2 -5 11 2 1 1 1 1\n'
                    '# ik e(k,n) Br(003)4p1/2-1/2 Br(004)4p1/2-1/2\n' + '\n'.join(rows) + '\n')
    obj = FPLOVisualizer(str(path))
    obj.parse_header_and_system()
    obj.read_and_parse_data(max_kpoints=2)
    assert obj.band_weights.shape == (11, 1, 2)
    widget.set_visualizer(obj, str(path))
    widget.current_plot_type = mode
    widget.visible_orbitals = {key: True for key in obj.orbital_info}
    widget.plot_current_view()
    ax = widget.figure.axes[0]
    np.testing.assert_array_equal(ax.collections[0].get_offsets()[:, 0], [0, 10])
    widget.zoom_to_region(4.5, 5.5, -.1, .1)
    ax = widget.figure.axes[0]
    np.testing.assert_allclose(ax.get_xlim(), [4.5, 5.5])
    np.testing.assert_allclose(ax.get_ylim(), [-.1, .1])
    np.testing.assert_array_equal(ax.collections[0].get_offsets(), [[5, 0]])
    np.testing.assert_allclose(ax.collections[0].get_sizes(), [40.4])
    assert obj.band_weights[5, 0, 0] == .8
    widget.reset_zoom()
    np.testing.assert_array_equal(widget.figure.axes[0].collections[0].get_offsets()[:, 0], [0, 10])


def test_toolbar_viewport_changes_request_full_data_resampling(widget, app, weight_file):
    obj = FPLOVisualizer(str(weight_file))
    obj.parse_header_and_system()
    obj.read_and_parse_data(max_kpoints=1)
    widget.set_visualizer(obj, str(weight_file))
    widget.visible_orbitals = {key: True for key in obj.orbital_info}
    widget.plot_current_view()
    ax = widget.figure.axes[0]
    ax.set_xlim(.9, 1.1)
    ax.set_ylim(-2, 2)
    widget.canvas.draw()
    app.processEvents()
    ax = widget.figure.axes[0]
    for collection in ax.collections:
        np.testing.assert_array_equal(collection.get_offsets()[:, 0], [1, 1])
    assert obj.num_kpoints == 3


def test_site_controls_expose_original_components_and_can_toggle_separately(app, weight_file):
    weight_file.write_text(weight_file.read_text().replace('Cs(001)5s1/2-1/2', 'Br(003)4p1/2-1/2')
                           .replace('Ag(002)4d3/2-3/2', 'Br(004)4p1/2-1/2'))
    obj = FPLOVisualizer(str(weight_file))
    obj.parse_header_and_system()
    obj.read_and_parse_data()
    panel = ControlPanel()
    panel.set_orbitals(obj)
    events = []
    panel.orbital_toggled.connect(lambda key, checked: events.append((key, checked)))
    panel.orbital_checkboxes['Br(003)_4p'].setChecked(True)
    assert events == [('Br(003)_4p', True)]
    assert not panel.orbital_checkboxes['Br(004)_4p'].isChecked()
    assert 'Br(003)4p1/2-1/2' in panel.orbital_checkboxes['Br(003)_4p'].toolTip()
    panel.close()


def test_shared_scale_does_not_change_when_other_groups_are_hidden(widget):
    widget.visualizer = SimpleNamespace(
        k_points=np.array([0., 1.]), band_energies=np.array([[0., 1.], [0., 1.]]),
        band_weights=np.array([[[.03, .8], [.8, .03]], [[.03, .8], [.8, .03]]]),
        orbital_info={'Br(003)_4p': [0], 'Br(004)_4p': [1]}, orbital_colors={}, num_bands=2)
    ax = RecordingAxes()
    widget._plot_orbital_weights_singlecore(ax, [-2, 2], .02, 1, .7, 2, 50, 10)
    np.testing.assert_allclose(ax.points[0][2]['s'], [3.44, 3.44, 40.4, 40.4])
    np.testing.assert_allclose(ax.points[1][2]['s'], [40.4, 40.4, 3.44, 3.44])
    widget.visible_orbitals = {'Br(003)_4p': False}
    other = RecordingAxes()
    widget._plot_orbital_weights_singlecore(other, [-2, 2], .02, 1, .7, 2, 50, 10)
    np.testing.assert_array_equal(other.points[0][2]['s'], ax.points[1][2]['s'])


def test_export_helpers_use_same_raw_scale_and_original_samples(weight_file, app):
    from matplotlib.figure import Figure
    from fplo_fermi_visualizer import FPLOFermiVisualizer

    complete = FPLOVisualizer(str(weight_file), configure_plot=False)
    complete.parse_header_and_system()
    complete.read_and_parse_data()
    fermi = FPLOFermiVisualizer(str(weight_file), configure_plot=False)
    k, energy, weight = np.array([0., 1., 2.]), np.zeros(3), np.array([.03, .8, .5])
    first, second = Figure().subplots(), Figure().subplots()
    complete._plot_dense_orbital_weight_points(first, k, energy, weight, 'red')
    fermi._plot_orbital_weight_points(second, k, energy, weight, 'red')
    np.testing.assert_array_equal(first.collections[0].get_offsets(), second.collections[0].get_offsets())
    np.testing.assert_allclose(first.collections[0].get_sizes(), [3.44, 40.4, 26])
    np.testing.assert_array_equal(first.collections[0].get_sizes(), second.collections[0].get_sizes())
    assert first._raw_weight_scale.get_title().get_text() == 'Raw weight (shared area scale)'
    complete._plot_dense_orbital_weight_points(first, k, energy, weight, 'blue')
    assert len(first.artists) == 1
