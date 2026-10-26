import pytest

from dmv_mat_cvd.data.synthetic import SyntheticDomainConfig, generate_cohort
from dmv_mat_cvd.data.splitting import split_source, split_target


@pytest.fixture
def source():
    return generate_cohort(SyntheticDomainConfig(160, "source", 7))


@pytest.fixture
def target():
    return generate_cohort(SyntheticDomainConfig(120, "target", 107))


@pytest.fixture
def source_parts(source):
    return split_source(source, seed=7)


@pytest.fixture
def target_parts(target):
    return split_target(target, seed=8)
