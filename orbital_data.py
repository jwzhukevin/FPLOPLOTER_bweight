"""Numerical helpers shared by the FPLO readers and Qt plots."""

import re
import os

import numpy as np


class AnalysisCancelled(Exception):
    """Cooperative cancellation, distinct from malformed scientific input."""


def check_cancelled(owner):
    check = getattr(owner, '_cancel_check', None)
    if check is not None and check():
        raise AnalysisCancelled()


def parse_orbital_columns(text):
    """Preserve each source label, atomic site and SOC component in column order."""
    tokens = re.sub(r'([A-Z][a-z]?)\s+(?=\(\d+\))', r'\1', text).split()
    if tokens and tokens[0] == '#':
        tokens = tokens[1:]
    if len(tokens) >= 2 and tokens[0] == 'ik' and tokens[1] == 'e(k,n)':
        tokens = tokens[2:]
    columns = []
    seen = set()
    for label in tokens:
        match = re.fullmatch(
            r'([A-Z][a-z]?)\((\d+)\)(\d*)([spdf])'
            r'((?:\d+/\d+[+-]\d+/\d+|[+-]?\d+(?:[+-]\d+/\d+)?)?)', label)
        if match is None:
            raise ValueError(f'Unrecognized orbital label at weight column {len(columns)}: {label!r}')
        if label in seen:
            raise ValueError(f'Duplicate orbital label: {label}')
        seen.add(label)
        element, site, principal, angular, component = match.groups()
        columns.append(dict(label=label, element=element, site=site,
                            shell=principal + angular, component=component))
    if not columns:
        raise ValueError('No orbital labels found')
    return columns


def parse_orbital_labels(text):
    """Sum components only within the same atomic site and shell."""
    groups = {}
    for index, column in enumerate(parse_orbital_columns(text)):
        key = f"{column['element']}({column['site']})_{column['shell']}"
        groups.setdefault(key, []).append(index)
    return groups


def _parse_header(first, second):
    parts = first.split()
    if len(parts) < 6 or parts[0] != '#' or not second.startswith('#'):
        raise ValueError('Missing or malformed FPLO weight header')
    try:
        header = dict(num_kpoints=int(parts[3]), num_orbitals=int(parts[4]),
                      num_bands=int(parts[5]), original_fermi_energy=float(parts[2]),
                      fermi_energy=0.0)
    except ValueError as exc:
        raise ValueError('Invalid numeric FPLO header fields') from exc
    if not np.isfinite(header['original_fermi_energy']) or any(
            header[key] <= 0 for key in ('num_kpoints', 'num_orbitals', 'num_bands')):
        raise ValueError('FPLO header requires finite EF and positive dimensions')
    columns = parse_orbital_columns(second)
    if len(columns) != header['num_orbitals']:
        raise ValueError('Orbital labels do not match the declared weight columns')
    return header, columns, parse_orbital_labels(second)


def read_weight_header(filename):
    with open(filename, encoding='utf-8-sig') as stream:
        return _parse_header(stream.readline(), stream.readline())


def _file_signature(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _read_weight_rows(stream, nk, nb, no, owner):
    """Validate each numeric record and the exact declared state count."""
    data = np.empty((nk * nb, no + 2), dtype=float)
    count = 0
    for line_number, line in enumerate(stream, start=3):
        check_cancelled(owner)
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split()
        if len(parts) != no + 2:
            raise ValueError(f'Line {line_number}: weight data width {len(parts)}; expected {no + 2}')
        if count == len(data):
            raise ValueError(f'Line {line_number}: extra data beyond declared k points and bands')
        try:
            row = np.asarray(parts, dtype=float)
        except ValueError as exc:
            raise ValueError(f'Line {line_number}: invalid numeric value') from exc
        if not np.isfinite(row).all():
            raise ValueError(f'Line {line_number}: non-finite energy, coordinate or weight')
        data[count] = row
        count += 1
    if count != len(data):
        raise ValueError(f'Truncated FPLO file: expected {len(data)} states, found {count}')
    return data


def read_weight_data(filename, expected_header, expected_columns, owner=None):
    """Validate and load every state; never truncate or sample scientific data.

    Energy values and signed weights are preserved exactly as parsed. The
    existing input convention is eV relative to EF; no shift/normalization is
    applied here. Repeated path coordinates are valid, including endpoints.
    """
    with open(filename, encoding='utf-8-sig') as stream:
        check_cancelled(owner)
        before = _file_signature(os.fstat(stream.fileno()))
        header, columns, _ = _parse_header(stream.readline(), stream.readline())
        if header != expected_header or columns != expected_columns:
            raise ValueError('FPLO header changed since it was parsed; reload the file')
        nk, nb, no = (header[key] for key in ('num_kpoints', 'num_bands', 'num_orbitals'))
        # A payload needs at least one byte per field. Reject impossible header
        # sizes before allocating, especially for truncated cluster transfers.
        if nk * nb * (no + 2) > before[2]:
            raise ValueError('Truncated FPLO file: declared dimensions exceed file size')
        data = _read_weight_rows(stream, nk, nb, no, owner)
        if before != _file_signature(os.fstat(stream.fileno())) or before != _file_signature(os.stat(filename)):
            raise ValueError('FPLO file changed while loading; wait for transfer/calculation completion')
    data = data.reshape(nk, nb, no + 2)
    if not np.all(data[:, :, 0] == data[:, :1, 0]):
        raise ValueError('Inconsistent k coordinate within a declared band block')
    if np.any(np.diff(data[:, 0, 0]) < 0):
        raise ValueError('FPLO path coordinates must be nondecreasing')
    data.setflags(write=False)
    return data[:, 0, 0], data[:, :, 1], data[:, :, 2:]


def weight_point_sizes(weights, min_size=2, max_size=50, factor=1.0):
    """Shared raw-weight area scale: 0 -> min_size, 1 -> max_size at factor 1.

    Values above one are not clipped; this is a display mapping, not a
    probability interpretation or a normalization of FPLO populations.
    """
    return min_size + np.asarray(weights) * (max_size - min_size) * factor


def grouped_weights(visualizer, orbital_key):
    """Cache exact sums until a reader replaces its source weight array.

    Readers treat loaded arrays as immutable. Cache keys also include the
    indices, so reparsing/replacing orbital groups cannot reuse stale sums.
    """
    source = visualizer.band_weights
    if getattr(visualizer, '_group_weight_source', None) is not source:
        visualizer._group_weight_source = source
        visualizer._group_weight_cache = {}
    indices = tuple(visualizer.orbital_info[orbital_key])
    key = (orbital_key, indices)
    cache = visualizer._group_weight_cache
    if key not in cache:
        cache[key] = np.take(source, indices, axis=2).sum(axis=2)
    return cache[key]


def prepare_weight_points(k_points, energies, weights, threshold, max_points, energy_range=None, k_range=None):
    """Sample only the visible points; leave full-resolution arrays untouched."""
    mask = weights > threshold
    if energy_range is not None:
        mask &= (energies >= energy_range[0]) & (energies <= energy_range[1])
    if k_range is not None:
        mask &= (k_points >= k_range[0]) & (k_points <= k_range[1])
    k, energy, weight = k_points[mask], energies[mask], weights[mask]
    if max_points is not None and (isinstance(max_points, bool) or
            not isinstance(max_points, (int, np.integer)) or max_points < 1):
        raise ValueError('Display point limit must be a positive integer or None')
    if max_points is not None and len(weight) > max_points:
        indices = ([int(np.argmax(weight))] if max_points == 1 else
                   np.linspace(0, len(weight) - 1, int(max_points), dtype=int))
        k, energy, weight = k[indices], energy[indices], weight[indices]
    return k, energy, weight


def bands_in_window(energies, window):
    """Include bands whose sampled piecewise-linear path intersects a window."""
    lower, upper = window
    if not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError('Energy window must have finite, ordered bounds')
    inside = np.any((energies >= lower) & (energies <= upper), axis=0)
    if len(energies) > 1:
        before, after = energies[:-1], energies[1:]
        crossing = (np.minimum(before, after) <= upper) & (np.maximum(before, after) >= lower)
        inside |= np.any(crossing, axis=0)
    return np.flatnonzero(inside).tolist()
