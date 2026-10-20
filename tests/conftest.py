import os
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'fplo-test-mpl'))

import pytest


@pytest.fixture
def weight_file(tmp_path):
    path = tmp_path / '+bweights'
    path.write_text(
        '# 1 -5.0 3 2 2 1 1 2\n'
        '# ik e(k,n) Cs(001)5s1/2-1/2 Ag(002)4d3/2-3/2\n'
        '0 -4 .25 .75\n0 3 .6 .4\n'
        '1 -1 .3 .7\n1 1 .4 .6\n'
        '2 .5 .2 .8\n2 2 .1 .9\n', encoding='utf-8',
    )
    return path
