"""Matplotlib display conventions shared by GUI and exported weight plots."""

import numpy as np
from matplotlib.legend import Legend
from matplotlib.lines import Line2D

from orbital_data import weight_point_sizes


def add_weight_scale(ax, settings=None):
    """Keep an independent raw-weight area key alongside the orbital legend."""
    if getattr(ax, '_raw_weight_scale', None) is not None:
        return ax._raw_weight_scale
    settings = settings or {}
    weights = (0.1, 0.5, 1.0)
    sizes = weight_point_sizes(weights, settings.get('point_min_size', 2),
                               settings.get('point_max_size', 50),
                               settings.get('point_size_factor', 1.0))
    handles = [Line2D([], [], linestyle='none', marker='o', color='gray',
                      markersize=np.sqrt(size)) for size in sizes]
    legend = Legend(ax, handles, [f'{weight:g}' for weight in weights],
                    title='Raw weight (shared area scale)', loc='lower left',
                    fontsize=8, title_fontsize=8, ncol=3, framealpha=.85)
    ax.add_artist(legend)
    ax._raw_weight_scale = legend
    return legend
