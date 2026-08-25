"""百炼图像画面扩展（扩图）HTTP 客户端（httpx 封装）。

封装百炼两步异步调用：创建任务（返回 task_id）+ 查询任务结果（返回结果图 URL）。
统一超时、轻量重试与异常翻译（httpx 异常 → ImageOutpaintingException 子类）。
"""

from typing import Any

import httpx

from ..logging import get_logger
from .exceptions import (
    OutpaintingParseError,
    OutpaintingRequestError,
    OutpaintingTimeoutError,
)
from .models import CreateTaskResponse, OutpaintingParameters, QueryTaskResponse, TaskStatus

logger = get_logger()


class BailianOutpaintingClient:
    """百炼扩图 API 客户端。

    仅需 base_url 与 api_key；create_task / query_task 已把百炼响应解析为
    内部模型，上层无需关心 JSON 结构。
    """

    CREATE_PATH = "/api/v1/services/aigc/image2image/out-painting"
    TASK_PATH = "/api/v1/tasks/{task_id}"
    MODEL = "image-out-painting"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._max_retries = max(0, max_retries)

    async def create_task(
        self, image_url: str, parameters: OutpaintingParameters
    ) -> CreateTaskResponse:
        """创建扩图任务，返回 task_id。"""
        payload = {
            "model": self.MODEL,
            "input": {"image_url": image_url},
            "parameters": parameters.to_request_params(),
        }
        data = await self._request_json(
            "POST",
            self.CREATE_PATH,
            json=payload,
            headers={"X-DashScope-Async": "enable", "Content-Type": "application/json"},
        )
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            raise OutpaintingParseError(f"创建任务响应缺少 task_id: {data}")
        return CreateTaskResponse(
            task_id=task_id,
            task_status=output.get("task_status", TaskStatus.PENDING.value),
        )

    async def query_task(self, task_id: str) -> QueryTaskResponse:
        """查询扩图任务状态与结果。"""
        data = await self._request_json("GET", self.TASK_PATH.format(task_id=task_id))
        output = data.get("output") or {}
        return QueryTaskResponse(
            task_id=output.get("task_id", task_id),
            task_status=output.get("task_status", TaskStatus.UNKNOWN.value),
            output_image_url=output.get("output_image_url"),
            code=data.get("code") or output.get("code"),
            message=data.get("message") or output.get("message"),
        )

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """发起 JSON 请求，对超时/5xx 轻量重试；非 2xx 或业务 code 错误抛异常。"""
        attempts = self._max_retries + 1
        last_exc: Exception | None = None

        for attempt in range(attempts):
            try:
                resp = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as e:
                last_exc = OutpaintingTimeoutError(f"{method} {url} 超时: {e}")
                logger.warning(f"扩图 HTTP 超时 {method} {url}", extra={"reason": "http_timeout"})
                continue
            except httpx.HTTPError as e:
                raise OutpaintingRequestError(f"{method} {url} 请求失败: {e}") from e

            # 5xx：轻量重试（默认不重试）
            if resp.status_code >= 500:
                last_exc = OutpaintingRequestError(
                    self._describe_error(resp, f"{method} {url} 返回 {resp.status_code}")
                )
                logger.warning(
                    f"扩图 HTTP 5xx {method} {url}",
                    extra={"reason": "http_5xx", "status_code": resp.status_code},
                )
                if attempt < attempts - 1:
                    continue
                raise last_exc

            # 非 2xx（4xx）：直接抛
            if resp.status_code >= 400:
                raise OutpaintingRequestError(
                    self._describe_error(resp, f"{method} {url} 返回 {resp.status_code}")
                )

            try:
                data = resp.json()
            except ValueError as e:
                raise OutpaintingParseError(f"{url} 返回非 JSON: {e}") from e

            if not isinstance(data, dict):
                raise OutpaintingParseError(f"{url} 响应不是 JSON 对象: {type(data).__name__}")

            # 百炼部分失败可能返回 200 + 顶层 code/message
            if data.get("code"):
                raise OutpaintingRequestError(
                    f"{method} {url} 业务错误: {data.get('code')} - {data.get('message', '')}"
                )

            return data

        raise last_exc or OutpaintingRequestError(f"{method} {url} 请求失败")

    @staticmethod
    def _describe_error(resp: httpx.Response, prefix: str) -> str:
        """从非 2xx 响应体提取百炼 code/message 作为可读错误信息。"""
        try:
            body = resp.json()
            if isinstance(body, dict) and body.get("code"):
                return f"{prefix}: {body.get('code')} - {body.get('message', '')}"
        except Exception:
            pass
        return f"{prefix}: {resp.text[:200]}"

    async def close(self) -> None:
        """关闭连接池。"""
        await self._client.aclose()
