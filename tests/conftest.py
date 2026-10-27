import pytest

from studio.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", max_jobs_per_day=0)
