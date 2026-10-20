import numpy as np
import pytest

from fplo_fermi_visualizer import FPLOFermiVisualizer


def bare(energies, fermi=0):
    obj = FPLOFermiVisualizer.__new__(FPLOFermiVisualizer)
    obj.band_energies = np.array(energies, dtype=float)
    obj.num_kpoints, obj.num_bands = obj.band_energies.shape
    obj.fermi_energy = fermi
    obj.user_fermi_window = 2.
    return obj


def test_metal_crossing_has_zero_gap_and_is_selected():
    obj = bare([[-2], [2]])
    window, _, _, gap = obj._analyze_fermi_region()
    assert window == (-1, 1)
    assert gap == 0
    assert obj.important_bands == [0]


def test_insulator_gap_is_preserved():
    obj = bare([[-2, 3], [-1, 2]])
    _, vbm, cbm, gap = obj._analyze_fermi_region()
    assert (vbm, cbm, gap) == (-1, 2, 3)


def test_shifted_reference_is_used_for_gap_and_window():
    obj = bare([[3, 8], [4, 7]], fermi=5)
    window, vbm, cbm, gap = obj._analyze_fermi_region()
    assert (window, vbm, cbm, gap) == ((4, 6), 4, 7, 3)


@pytest.mark.parametrize('grid', [np.arange(-.2, .21, .1), np.array([0.])])
def test_automatic_window_handles_narrow_and_constant_spectra(grid):
    obj = bare([[-.1], [.1]])
    lower, upper = obj._adaptive_boundary_selection(grid, np.ones_like(grid), 'metal', -.1, .1, 0)
    assert np.isfinite([lower, upper]).all()
    assert lower <= -3 and upper >= 3


@pytest.mark.parametrize('size', [0, -2, float('nan'), float('inf')])
def test_invalid_user_window_does_not_mutate_state(size):
    obj = bare([[-2], [2]])
    obj.energy_window = (-1, 1)
    with pytest.raises(ValueError):
        obj.set_fermi_window(size)
    assert obj.user_fermi_window == 2
    assert obj.energy_window == (-1, 1)


def test_constructor_then_analysis_does_not_double_count(weight_file, monkeypatch):
    obj = FPLOFermiVisualizer(str(weight_file))
    monkeypatch.setattr(obj, 'create_output_folder', lambda: None)
    monkeypatch.setattr(obj, 'plot_fermi_band_structure', lambda: 'unused')
    monkeypatch.setattr(obj, 'plot_fermi_orbital_weights', lambda: ('unused', 'unused'))
    monkeypatch.setattr(obj, 'plot_fermi_individual_orbitals', lambda: [])
    monkeypatch.setattr(obj, '_print_fermi_summary', lambda *args: None)
    result = obj.run_fermi_analysis(max_kpoints=None)
    assert obj.orbital_info == {'Cs(001)_5s': [0], 'Ag(002)_4d': [1]}
    assert result['fermi_info']['band_gap'] == 0
