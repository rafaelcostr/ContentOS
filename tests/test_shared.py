import pytest
from contentos_shared.enums import JobStatus, PipelineStep


def test_pipeline_steps_order():
    steps = PipelineStep.ordered()
    assert len(steps) == 9
    assert steps[0] == PipelineStep.RESEARCH
    assert steps[-1] == PipelineStep.PUBLISHER


def test_job_status_values():
    assert JobStatus.RETRYING.value == "retrying"
    assert JobStatus.FAILED.value == "failed"
