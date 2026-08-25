"""image_outpainting 数据模型单元测试。"""

import pytest
from pydantic import ValidationError

from src.infrastructure.image_outpainting.models import (
    CreateTaskResponse,
    OutpaintingParameters,
    QueryTaskResponse,
    TaskStatus,
)


def test_parameters_defaults_all_none():
    p = OutpaintingParameters()
    assert p.to_request_params() == {}


def test_parameters_excludes_none():
    p = OutpaintingParameters(x_scale=1.5, add_watermark=False)
    assert p.to_request_params() == {"x_scale": 1.5, "add_watermark": False}


def test_parameters_accepts_all_modes():
    p = OutpaintingParameters(
        angle=45,
        output_ratio="4:3",
        x_scale=1.5,
        y_scale=1.2,
        top_offset=100,
        left_offset=200,
        best_quality=True,
        limit_image_size=True,
    )
    params = p.to_request_params()
    assert params["angle"] == 45
    assert params["output_ratio"] == "4:3"
    assert params["top_offset"] == 100


def test_x_scale_out_of_range_rejected():
    with pytest.raises(ValidationError):
        OutpaintingParameters(x_scale=4.0)


def test_x_scale_below_one_rejected():
    with pytest.raises(ValidationError):
        OutpaintingParameters(x_scale=0.5)


def test_output_ratio_invalid_rejected():
    with pytest.raises(ValidationError):
        OutpaintingParameters(output_ratio="2:1")


def test_angle_out_of_range_rejected():
    with pytest.raises(ValidationError):
        OutpaintingParameters(angle=360)


def test_extra_field_forbidden():
    with pytest.raises(ValidationError):
        OutpaintingParameters(foo=1)


def test_create_task_response():
    r = CreateTaskResponse(task_id="t-1", task_status=TaskStatus.PENDING.value)
    assert r.task_id == "t-1"
    assert r.task_status == "PENDING"


def test_query_task_response_succeeded():
    r = QueryTaskResponse(
        task_id="t-1", task_status=TaskStatus.SUCCEEDED.value, output_image_url="http://res/img.jpg"
    )
    assert r.output_image_url == "http://res/img.jpg"
    assert r.code is None
    assert r.message is None
