"""Independent null/shift scale audit; never used to choose a selector."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from dmv_mat_cvd.transfer.calibration import permutation_mmd
from dmv_mat_cvd.transfer.scores import multi_kernel_mmd, normalize_representations


def run(replicates=40):
    torch.set_num_threads(1)
    rows = []
    max_scale_difference = 0.
    for dimension in (4, 16, 32, 64):
        for shifted in (False, True):
            collected = []
            for seed in range(replicates):
                rng = np.random.default_rng(seed + 30000)
                x = rng.normal(size=(64, dimension))
                y = rng.normal(size=(96, dimension)) + (.8 if shifted else 0.)
                evidence = permutation_mmd(x, y, permutations=199, seed=seed)
                for scale in (.1, 10.):
                    scaled = permutation_mmd(x * scale, y * scale, permutations=199, seed=seed)
                    max_scale_difference = max(max_scale_difference,
                        abs(scaled['permutation_mmd'] - evidence['permutation_mmd']),
                        abs(scaled['domain_p'] - evidence['domain_p']))
                xs, ys, _ = normalize_representations(x, y)
                collected.append({'p': evidence['domain_p'], 'observed': evidence['permutation_mmd'],
                    'null_mean': evidence['null_mean'], 'null_std': evidence['null_std'],
                    'raw': multi_kernel_mmd(x, y), 'source_rms': multi_kernel_mmd(xs, ys)})
            rows.append({'dimension': dimension, 'shifted': shifted, 'replicates': replicates,
                'p_mean': float(np.mean([r['p'] for r in collected])),
                'p_le_005_rate': float(np.mean([r['p'] <= .05 for r in collected])),
                **{key + '_mean': float(np.mean([r[key] for r in collected]))
                   for key in ('observed', 'null_mean', 'null_std', 'raw', 'source_rms')}})
    return {'source_n': 64, 'target_n': 96, 'permutations': 199,
            'seed_range': [30000, 30000 + replicates - 1], 'groups': rows,
            'maximum_common_rescaling_difference': max_scale_difference,
            'interpretation': 'Independent Gaussian instrument audit, not clinical inference or policy tuning.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replicates', type=int, default=40)
    args = parser.parse_args()
    result = run(args.replicates)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
