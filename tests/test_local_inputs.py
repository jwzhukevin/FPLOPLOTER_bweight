"""Additional checks for local scientific fixtures, when present in the checkout."""

from pathlib import Path
import re

import numpy as np
import pytest

from fplo_visualizer import FPLOVisualizer
from orbital_data import grouped_weights


ROOT = Path(__file__).resolve().parents[1]
INPUTS = [p for p in [ROOT / '+bweights', *sorted(ROOT.glob('*/+bweights'))] if p.is_file()]


@pytest.mark.parametrize('path', INPUTS, ids=[str(path.relative_to(ROOT)) for path in INPUTS])
def test_real_header_mapping_and_weight_sums(path):
    obj = FPLOVisualizer(str(path))
    obj.parse_header_and_system()
    with path.open() as stream:
        next(stream)
        header = next(stream)
        sample = []
        for line in stream:
            if line.strip() and not line.startswith('#'):
                sample.append(np.fromstring(line, sep=' '))
                if len(sample) == 3:
                    break
    # Independently recover column order from the raw header.
    reference = {}
    for index, (element, site, shell) in enumerate(re.findall(r'([A-Z][a-z]?)\s*\((\d+)\)(\d+[spdf])', header)):
        reference.setdefault(f'{element}({site})_{shell}', []).append(index)
    assert obj.orbital_info == reference
    obj.band_weights = np.array(sample)[:, None, 2:]
    indices = sorted(i for values in obj.orbital_info.values() for i in values)
    assert indices == list(range(obj.band_weights.shape[2]))
    assert len(indices) == obj.header_info['num_orbitals']
    grouped_sum = sum(grouped_weights(obj, key) for key in obj.orbital_info)
    np.testing.assert_allclose(grouped_sum, obj.band_weights.sum(axis=2), atol=1e-12)
    obj.parse_header_and_system()
    np.testing.assert_allclose(sum(grouped_weights(obj, key) for key in obj.orbital_info), grouped_sum, atol=1e-12)
