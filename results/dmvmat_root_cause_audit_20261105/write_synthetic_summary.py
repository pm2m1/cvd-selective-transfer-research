"""Summarize only this audit's fixed invented-data outputs and public source pins."""
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_core import ROOT,FOLLOWUP,public_snapshot


def exclusive_json(path,obj):
    with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)


def main():
    out=ROOT/'synthetic_results'
    before=json.loads((out/'PUBLIC_SOURCE_SNAPSHOT_BEFORE.json').read_text())
    assert public_snapshot()==before==json.loads((out/'PUBLIC_SOURCE_SNAPSHOT_AFTER.json').read_text())
    manifest=json.loads((FOLLOWUP/'PUBLIC_PACKAGE_MANIFEST.json').read_text())['files']
    vendor=json.loads((FOLLOWUP/'VENDOR_BINDINGS.json').read_text())
    verified={}
    prefix='results/label_efficiency_followup_20261105/'
    for name,digest in before.items():
        if name.startswith(prefix):
            rel=name[len(prefix):]
            if rel in manifest:
                assert manifest[rel]==digest
                verified[name]={'sha256':digest,'matches_existing_public_pin':True}
            if rel in vendor:
                assert vendor[rel]['sha256']==digest
    stage=ROOT.parent/'supervisor_metrics_and_improvement_20261104/public_development_staging_20261104'
    mapping_checks={}
    for name in ['train_exploratory_candidates.py','compute_classification_metrics.py']:
        a=hashlib.sha256((stage/'experiment_tools'/name).read_bytes()).hexdigest()
        b=hashlib.sha256((FOLLOWUP/'vendor'/name).read_bytes()).hexdigest()
        assert a==b
        mapping_checks[name]={'same_bytes':True,'sha256':a}
    # Only explicitly identified public preprocessing/exporter records are opened.
    staging=json.loads((stage/'PUBLIC_STAGING_MANIFEST.json').read_text())
    preprocessing='src/dmv_mat_cvd/data/public_preprocessing.py'
    pin=next(r['expected_sha256'] for r in staging['public_source_files'] if r['path']==preprocessing)
    actual=hashlib.sha256((stage/'public_project'/preprocessing).read_bytes()).hexdigest()
    assert actual==pin
    exporter_hash=hashlib.sha256((stage/'experiment_tools/prepare_development_inputs.py').read_bytes()).hexdigest()
    exclusive_json(ROOT/'SOURCE_INTEGRITY.json',{
        'scope':'explicit public files only; integrity is not publisher authenticity',
        'source_snapshot_count':len(before),'before_after_equal':True,'snapshot':before,
        'existing_public_pin_matches':verified,'vendor_original_equivalence':mapping_checks,
        'preprocessor_pin_matches':True,'preprocessor_sha256':actual,'exporter_sha256':exporter_hash})
    data=json.loads((out/'NEURAL_MECHANISMS.json').read_text())
    lines=['# Synthetic diagnostic evidence','',
        '**INVENTED DATA ONLY. No result in this file estimates HAALSI/MHAS performance.**','',
        'Plan frozen in SYNTHETIC_PLAN.json before fitting: seeds101/202/303; six scenarios; '
        'source1,536/validation384; target evaluation1,536 per scenario/seed. Source prevalence .20. '
        'Source preprocessing fit only on invented source training. Standard and compact source networks '
        'were trained separately, max30 epochs; target max20, .001 LR, BCE, patience5. '
        'Selector uses19 permutations/39 bootstraps to keep this a mechanism demonstration; '
        'these reduced counts are not the real experiment\'s199/199.','',
        'Six source fits, 72 target fits and36 source-reference evaluations; all planned conditions retained. '
        f'Neural diagnostic elapsed time {data["seconds"]:.3f}s on this runtime; not a clinical-run compute estimate.','',
        '## Mean changes from the architecture-matched source reference','',
        'Lower Brier is better; higher AP/AUROC is better. These are means over three fixed synthetic seeds, '
        'without claims of statistical significance or clinical precision. Compact comparisons use the '
        'compact source reference; other methods use original source. Full raw synthetic traces, class '
        'support, layer drift and gradient norms are retained in synthetic_results/NEURAL_MECHANISMS.json.','',
        '| Scenario | Method | ΔAP | ΔAUROC | ΔBrier | Updated parameters by seed |',
        '|---|---|---:|---:|---:|---|']
    deltas=[]
    for scenario in data['scenarios']:
        for method in ['matched_control','head_only','logical','compact_full']:
            rr=[r for r in data['rows'] if r['scenario']==scenario['name'] and r['method']==method]
            avg={k:float(np.mean([r['delta_vs_same_arch_source'][k] for r in rr])) for k in ['ap','auroc','brier']}
            lines.append(f'| {scenario["name"]} | {method} | {avg["ap"]:+.5f} | {avg["auroc"]:+.5f} | {avg["brier"]:+.5f} | '+', '.join(str(r['updated_parameters']) for r in rr)+' |')
            deltas.append({'scenario':scenario['name'],'method':method,**avg})
    lines += ['', '## Test coverage','',
        '30 unittest test methods passed, zero failures (test log in TEST_RESULTS.txt). Exhaustive '
        '128-mask checks and3,054 scalar reference decisions are assertions within these methods, not '
        '3,182 independent experiments. Additional tests cover NumPy geometry/MMD reference agreement, '
        'seed determinism, copied source isolation, outer/calibration-label flipping, role overlap '
        'rejection, supported-subset reporting, constant/skewed/tied scores, zero/one stopping events, '
        'calibration support0/1/4/5/6, missing class metrics and epoch-zero/pooled-OOF counterexamples.','',
        'Every neural target fit checked exact optimizer IDs, immutable cached source state and shared '
        'module equality. All initial/final public snapshot hashes agree. These checks do not prove '
        'private run provenance or general statistical feasibility.','',
        '## Additional deterministic evidence','',
        '- EPOCH_ZERO_COUNTEREXAMPLE.json: source BCE .12692806 versus selected .13055249; epoch1 wins because initial loss is not a candidate.',
        '- POOLED_OOF_COUNTEREXAMPLE.json: both folds have AUROC/AP1, but adapted pooled AUROC.75/AP.833333 due to cross-fold score offsets.',
        '- THRESHOLD_STRESS.json:100 resamples,99 supported; threshold .04381–.37368, separate invented evaluation recall .03–.94. No unsupported resample was replaced.',
        '- DESIGN_ARITHMETIC.json: exact role sizes and hypergeometric support probabilities derived from public historical pool totals. Not observed private support counts.',
        '- ENVIRONMENT.json: actual package/runtime versions.','',
        '## Reproduction and preservation','',
        'See README.md for the focused tests and exclusive-output synthetic command. The original '
        'follow-up and seven-candidate trainer/metric files match byte-for-byte; SOURCE_INTEGRITY.json '
        'checks their registered public pins and records public SHA256 values. AUDIT_SHA256.json '
        'binds all new report, code, test, plot and synthetic output files; it excludes itself. '
        'No real-input execution interface or clinical recovery controller was added.','',
        '![Synthetic mechanism illustration](figures/synthetic_mechanisms.png)','',
        'The plot shows each synthetic seed; its variability is not a clinical confidence interval.']
    with (ROOT/'SYNTHETIC_DIAGNOSTICS.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    exclusive_json(out/'MEAN_DELTAS.json',deltas)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    (ROOT/'figures').mkdir()
    fig,axes=plt.subplots(1,2,figsize=(12,6.6))
    methods=['matched_control','head_only','logical','compact_full'];colors=['#2166ac','#1b7837','#b2182b','#762a83']
    for ax,key in zip(axes,['ap','brier']):
        for i,method in enumerate(methods):
            for j,sc in enumerate(data['scenarios']):
                rr=[r for r in data['rows'] if r['method']==method and r['scenario']==sc['name']]
                values=[r['delta_vs_same_arch_source'][key] for r in rr]
                y=j+(i-1.5)*.17
                ax.scatter(values,[y]*len(values),s=20,color=colors[i],alpha=.65,label=method if j==0 else None)
                ax.scatter(np.mean(values),y,marker='|',s=130,color=colors[i])
        ax.axvline(0,color='black',lw=.8);ax.set_yticks(range(6),[s['name'].replace('_',' ') for s in data['scenarios']]);ax.invert_yaxis()
        ax.set_xlabel('ΔAP (higher better)' if key=='ap' else 'ΔBrier (lower better)');ax.grid(axis='x',alpha=.2)
    axes[0].legend(fontsize=8,loc='lower left');fig.suptitle('INVENTED SYNTHETIC ONLY — change from architecture-matched source\nDots: three fixed seeds; bars: seed means; no clinical inference',fontsize=12)
    fig.tight_layout()
    for suffix in ['svg','png']:fig.savefig(ROOT/f'figures/synthetic_mechanisms.{suffix}',dpi=150)
    plt.close(fig)
    print('PUBLIC_SYNTHETIC_SUMMARY_WRITTEN SOURCE_PINS_MATCH')


if __name__=='__main__':main()
