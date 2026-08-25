"""image_outpainting 门面便捷入口与单例开关单元测试。"""

from types import SimpleNamespace

import pytest

from src.infrastructure.image_outpainting.facade import (
    create_outpainting_task,
    get_image_outpainting_facade,
    query_outpainting_task,
    set_image_outpainting_facade,
)
from src.infrastructure.image_outpainting.models import OutpaintingParameters


@pytest.mark.asyncio
async def test_create_task_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.image_outpainting.facade.get_image_outpainting_facade", lambda: None
    )
    result = await create_outpainting_task("http://img", OutpaintingParameters())
    assert result is None


@pytest.mark.asyncio
async def test_query_task_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.image_outpainting.facade.get_image_outpainting_facade", lambda: None
    )
    result = await query_outpainting_task("t-1")
    assert result is None


def test_get_facade_none_when_disabled(monkeypatch):
    set_image_outpainting_facade(None)  # 清空单例，避免缓存
    fake = SimpleNamespace(IMAGE_OUTPAINTING_ENABLED=False)
    monkeypatch.setattr("src.infrastructure.image_outpainting.facade.get_settings", lambda: fake)
    assert get_image_outpainting_facade() is None


def test_get_facade_none_when_missing_key(monkeypatch):
    set_image_outpainting_facade(None)
    fake = SimpleNamespace(
        IMAGE_OUTPAINTING_ENABLED=True,
        IMAGE_OUTPAINTING_API_KEY="",
        IMAGE_OUTPAINTING_WORKSPACE_ID="ws-x",
    )
    monkeypatch.setattr("src.infrastructure.image_outpainting.facade.get_settings", lambda: fake)
    assert get_image_outpainting_facade() is None


def test_get_facade_none_when_missing_workspace(monkeypatch):
    set_image_outpainting_facade(None)
    fake = SimpleNamespace(
        IMAGE_OUTPAINTING_ENABLED=True,
        IMAGE_OUTPAINTING_API_KEY="sk-x",
        IMAGE_OUTPAINTING_WORKSPACE_ID="",
    )
    monkeypatch.setattr("src.infrastructure.image_outpainting.facade.get_settings", lambda: fake)
    assert get_image_outpainting_facade() is None
