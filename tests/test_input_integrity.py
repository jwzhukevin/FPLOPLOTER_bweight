"""Input contracts for local inspection of completed cluster weight files."""

from types import SimpleNamespace

import numpy as np
import pytest

import orbital_data
from orbital_data import parse_orbital_columns, read_weight_header, read_weight_data
from fplo_visualizer import FPLOVisualizer
from fplo_fermi_visualizer import FPLOFermiVisualizer


def corrupt(text, case):
    lines = text.splitlines()
    if case == 'missing_state':
        lines.pop()
    elif case == 'missing_k_block':
        lines = lines[:-2]
    elif case == 'extra_state':
        lines.append(lines[-1])
    elif case == 'extra_column':
        lines[3] += ' .1'
    elif case == 'short_row':
        lines[3] = '0 3'
    elif case == 'band_count':
        lines[0] = lines[0].replace('3 2 2', '3 2 3')
    elif case == 'k_count':
        lines[0] = lines[0].replace('3 2 2', '4 2 2')
    elif case == 'block_coordinate':
        lines[3] = '0.1 3 .6 .4'
    elif case == 'backward_path':
        lines[6:] = ['.5 .5 .2 .8', '.5 2 .1 .9']
    else:
        lines[4] = lines[4].replace('-1', case)
    return '\n'.join(lines) + '\n'


@pytest.mark.parametrize('reader', [FPLOVisualizer, FPLOFermiVisualizer])
@pytest.mark.parametrize('case', [
    'missing_state', 'missing_k_block', 'extra_state', 'extra_column', 'short_row',
    'band_count', 'k_count', 'block_coordinate', 'backward_path',
    'nan', 'inf', '-inf', '1.2bad',
])
def test_rejects_incomplete_or_inconsistent_payload(reader, case, weight_file):
    weight_file.write_text(corrupt(weight_file.read_text(), case))
    with pytest.raises(ValueError):
        obj = reader(str(weight_file), configure_plot=False)
        obj.parse_header_and_system()
        obj.read_and_parse_data()


@pytest.mark.parametrize('header', ['', '# broken', '# 1 invalid 3 2 2', '# 1 nan 3 2 2',
                                    '# 1 -5 0 2 2', '# 1 -5 3 3 2'])
def test_rejects_invalid_header(header, weight_file):
    lines = weight_file.read_text().splitlines()
    weight_file.write_text('\n'.join([header] + lines[1:]) + '\n')
    with pytest.raises(ValueError):
        read_weight_header(weight_file)


@pytest.mark.parametrize('labels', ['Cs(001)5sBAD', 'Cs(001)5s Cs(001)5s'])
def test_rejects_unknown_suffix_or_duplicate_column(labels):
    with pytest.raises(ValueError):
        parse_orbital_columns(labels)


def test_metadata_preserves_original_soc_components():
    columns = parse_orbital_columns('# ik e(k,n) Br(003)4p1/2-1/2 Br (004)4p3/2+3/2')
    assert [c['site'] for c in columns] == ['003', '004']
    assert [c['component'] for c in columns] == ['1/2-1/2', '3/2+3/2']
    assert columns[1]['label'] == 'Br(004)4p3/2+3/2'


def test_header_change_between_reads_is_rejected(weight_file):
    header, columns, _ = read_weight_header(weight_file)
    weight_file.write_text(weight_file.read_text().replace('Cs(001)', 'Cs(003)'))
    with pytest.raises(ValueError, match='changed'):
        read_weight_data(weight_file, header, columns)


def test_file_change_during_read_is_rejected(weight_file, monkeypatch):
    header, columns, _ = read_weight_header(weight_file)
    original = orbital_data._file_signature
    calls = []

    def changed(stat):
        signature = original(stat)
        calls.append(signature)
        return signature if len(calls) == 1 else (*signature[:-1], signature[-1] + 1)

    monkeypatch.setattr(orbital_data, '_file_signature', changed)
    with pytest.raises(ValueError, match='changed while loading'):
        read_weight_data(weight_file, header, columns)


def test_read_can_be_cancelled(weight_file):
    header, columns, _ = read_weight_header(weight_file)
    calls = []

    def cancel():
        calls.append(1)
        return len(calls) > 3

    with pytest.raises(orbital_data.AnalysisCancelled):
        read_weight_data(weight_file, header, columns, SimpleNamespace(_cancel_check=cancel))


@pytest.mark.parametrize('reader', [FPLOVisualizer, FPLOFermiVisualizer])
def test_failed_reload_retains_previous_complete_arrays(reader, weight_file):
    obj = reader(str(weight_file), configure_plot=False)
    obj.parse_header_and_system()
    obj.read_and_parse_data(max_kpoints=1)
    previous = obj.k_points, obj.band_energies, obj.band_weights
    weight_file.write_text(corrupt(weight_file.read_text(), 'missing_state'))
    with pytest.raises(ValueError):
        obj.read_and_parse_data()
    assert all(before is after for before, after in zip(
        previous, (obj.k_points, obj.band_energies, obj.band_weights)))


def test_valid_repeated_coordinates_and_nonzero_origin_are_preserved(weight_file):
    lines = weight_file.read_text().splitlines()
    for index, coordinate in enumerate([5, 5, 5, 5, 6, 6], start=2):
        lines[index] = str(coordinate) + ' ' + lines[index].split(' ', 1)[1]
    weight_file.write_text('\n'.join(lines) + '\n')
    obj = FPLOVisualizer(str(weight_file), configure_plot=False)
    obj.parse_header_and_system()
    obj.read_and_parse_data(max_kpoints=1)
    np.testing.assert_array_equal(obj.k_points, [5, 5, 6])
    assert obj.band_weights.shape == (3, 2, 2)
    assert not obj.band_weights.flags.writeable
    assert not obj.band_energies.flags.writeable


def test_signed_weights_are_preserved_without_clipping_or_normalizing(weight_file):
    weight_file.write_text(weight_file.read_text().replace('.25 .75', '-.25 1.75'))
    obj = FPLOVisualizer(str(weight_file), configure_plot=False)
    obj.parse_header_and_system()
    obj.read_and_parse_data()
    np.testing.assert_array_equal(obj.band_weights[0, 0], [-.25, 1.75])
    assert obj.validation_warnings


def test_impossible_dimensions_are_rejected_before_allocation(weight_file):
    weight_file.write_text(weight_file.read_text().replace('3 2 2', '100000000 2 2'))
    header, columns, _ = read_weight_header(weight_file)
    with pytest.raises(ValueError, match='dimensions exceed file size'):
        read_weight_data(weight_file, header, columns)


def test_record_reader_enforces_count_and_allows_blank_comment_lines():
    import io

    rows = '\n# path marker\n0 -1 .25 .75\n'
    parsed = orbital_data._read_weight_rows(io.StringIO(rows), 1, 1, 2, None)
    np.testing.assert_array_equal(parsed, [[0, -1, .25, .75]])
    with pytest.raises(ValueError, match='expected 2 states, found 1'):
        orbital_data._read_weight_rows(io.StringIO(rows), 2, 1, 2, None)
