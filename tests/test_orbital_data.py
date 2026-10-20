from types import SimpleNamespace

import numpy as np
import pytest

from orbital_data import bands_in_window, grouped_weights, parse_orbital_labels, prepare_weight_points, weight_point_sizes
from fplo_visualizer import FPLOVisualizer
from fplo_fermi_visualizer import FPLOFermiVisualizer


@pytest.mark.parametrize('reader', [FPLOVisualizer, FPLOFermiVisualizer])
def test_repeated_header_preserves_exact_weights(reader, weight_file):
    obj = reader(str(weight_file))
    obj.parse_header_and_system()
    obj.read_and_parse_data()
    first = {key: grouped_weights(obj, key).copy() for key in obj.orbital_info}
    obj.parse_header_and_system()
    assert obj.header_info['num_bands'] == obj.num_bands == 2
    assert obj.orbital_info == {'Cs(001)_5s': [0], 'Ag(002)_4d': [1]}
    for key in first:
        np.testing.assert_array_equal(grouped_weights(obj, key), first[key])
    np.testing.assert_allclose(sum(grouped_weights(obj, key) for key in first), 1)


def test_parser_preserves_sites_and_shells_and_sums_only_components():
    groups = parse_orbital_labels(
        'ik e(k,n) Cs (001)5s1/2-1/2 Cs(001)5s1/2+1/2 '
        'Cs(002)5s1/2-1/2 Cs(001)6s1/2-1/2 Ag(003)4d3/2-3/2'
    )
    assert groups == {'Cs(001)_5s': [0, 1], 'Cs(002)_5s': [2], 'Cs(001)_6s': [3], 'Ag(003)_4d': [4]}


def test_parser_accepts_labels_without_column_titles_and_legacy_shell():
    assert parse_orbital_labels('Cs(001)s Ag (002)4d') == {'Cs(001)_s': [0], 'Ag(002)_4d': [1]}


def test_one_k_point_window_selection():
    assert bands_in_window(np.array([[-2., 0., 2.]]), [-1, 1]) == [1]


def test_failed_header_parse_preserves_previous_mapping(weight_file):
    obj = FPLOVisualizer(str(weight_file))
    obj.parse_header_and_system()
    before = dict(obj.orbital_info)
    with pytest.raises(ValueError):
        obj._parse_orbital_labels('ik e(k,n) UNKNOWN Ag(002)4d')
    assert obj.orbital_info == before


@pytest.mark.parametrize('label', ['UNKNOWN', 'Cs(001)5g', ''])
def test_unknown_label_cannot_shift_following_columns(label):
    with pytest.raises(ValueError):
        parse_orbital_labels(f'ik e(k,n) {label}' if not label else
                             f'ik e(k,n) Cs(001)5s {label} Ag(002)4d')


def test_cache_reuses_sums_and_invalidates_on_data_or_indices_change():
    obj = SimpleNamespace(band_weights=np.arange(24.).reshape(3, 2, 4),
                          orbital_info={'Cs_5s': [0, 2]})
    original = obj.band_weights.copy()
    a = grouped_weights(obj, 'Cs_5s')
    np.testing.assert_array_equal(a, original[:, :, 0] + original[:, :, 2])
    assert grouped_weights(obj, 'Cs_5s') is a
    obj.orbital_info['Cs_5s'] = [1]
    np.testing.assert_array_equal(grouped_weights(obj, 'Cs_5s'), original[:, :, 1])
    obj.band_weights = original * 2
    np.testing.assert_array_equal(grouped_weights(obj, 'Cs_5s'), original[:, :, 1] * 2)
    np.testing.assert_array_equal(original, np.arange(24.).reshape(3, 2, 4))


def test_filter_window_before_top_n_and_keep_strict_threshold():
    k, energy, weights = prepare_weight_points(
        np.arange(4), np.array([-10., 0., 1., 2.]), np.array([.9, .1, .2, .02]),
        .02, 1, [-1, 3],
    )
    np.testing.assert_array_equal(k, [2])
    np.testing.assert_array_equal(energy, [1])
    np.testing.assert_array_equal(weights, [.2])


def test_band_selection_includes_crossings_edges_and_rejects_outside():
    energies = np.array([[-2, -4, 2, -1, .5], [2, -3, 3, -1, .7]])
    assert bands_in_window(energies, [-1, 1]) == [0, 3, 4]


@pytest.mark.parametrize('window', [[1, -1], [float('nan'), 1], [0, float('inf')]])
def test_invalid_band_window_is_rejected(window):
    with pytest.raises(ValueError):
        bands_in_window(np.array([[-1.], [1.]]), window)


@pytest.mark.parametrize('reader', [FPLOVisualizer, FPLOFermiVisualizer])
def test_reader_rejects_consistently_wrong_weight_width(reader, weight_file):
    text = weight_file.read_text().replace(' .25 .75', ' .25').replace(' .6 .4', ' .6')
    # Use a consistently short payload to check the declared column contract.
    lines = text.splitlines()
    weight_file.write_text('\n'.join(lines[:2] + [' '.join(row.split()[:3]) for row in lines[2:]]) + '\n')
    with pytest.raises(ValueError, match='width'):
        obj = reader(str(weight_file))
        obj.parse_header_and_system()
        obj.read_and_parse_data()


@pytest.mark.parametrize('reader', [FPLOVisualizer, FPLOFermiVisualizer])
def test_display_limit_does_not_change_full_data_or_analysis(reader, weight_file):
    obj = reader(str(weight_file), configure_plot=False)
    obj.parse_header_and_system()
    obj.read_and_parse_data(max_kpoints=1)
    np.testing.assert_array_equal(obj.k_points, [0, 1, 2])
    np.testing.assert_array_equal(obj.band_energies, [[-4, 3], [-1, 1], [.5, 2]])
    assert obj.band_weights.shape == (3, 2, 2)
    assert obj.plot_max_kpoints == 1
    if reader is FPLOFermiVisualizer:
        assert obj._analyze_fermi_region()[3] == 0


def test_display_sampling_keeps_endpoints_and_filters_viewport_first():
    k = np.arange(11.)
    energies, weights = np.zeros(11), np.full(11, .3)
    np.testing.assert_array_equal(prepare_weight_points(k, energies, weights, .02, 3)[0], [0, 5, 10])
    np.testing.assert_array_equal(prepare_weight_points(k, energies, weights, .02, 3, k_range=[4, 6])[0], [4, 5, 6])
    np.testing.assert_array_equal(k, np.arange(11.))


def test_raw_weight_scale_is_linear_and_does_not_clip_weights_over_one():
    np.testing.assert_allclose(weight_point_sizes([0, .03, .5, .8, 1, 1.5]), [2, 3.44, 26, 40.4, 50, 74])


@pytest.mark.parametrize('limit', [0, -1, 1.5, True, float('nan'), float('inf')])
def test_invalid_display_limits_are_rejected(limit):
    with pytest.raises(ValueError, match='positive integer'):
        prepare_weight_points(np.array([0]), np.array([0]), np.array([1]), .02, limit)
