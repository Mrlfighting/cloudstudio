"""拼豆取图服务测试：真实解码、来源限制与有界传输。"""

from io import BytesIO

import httpx
import pytest
from fastapi import HTTPException
from PIL import Image

from src.modules.bead_pattern.service import MAX_BYTES, BeadSourceService, inspect_image, validate_source_url

BASE = "https://example.cos.ap-guangzhou.myqcloud.com"
URL = BASE + "/pictures/test.png"


def image_bytes(fmt: str = "PNG") -> bytes:
    """内存生成真实图片，不依赖网络或本机文件。"""
    buffer = BytesIO()
    Image.new("RGB", (20, 10), "red").save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("GIF", "image/gif")],
)
def test_real_formats(fmt, mime):
    """依据实际字节识别四种允许格式。"""
    assert inspect_image(image_bytes(fmt)) == mime


@pytest.mark.parametrize("url", [
    "http://example.cos.ap-guangzhou.myqcloud.com/pictures/x.png",
    "https://evil.example/pictures/x.png", BASE + ".evil.test/pictures/x.png",
    "https://user:password@example.cos.ap-guangzhou.myqcloud.com/pictures/x.png",
    BASE + "/pictures/%2e%2e/secret", BASE + "/other/file.png", BASE + ":444/pictures/x.png",
    BASE + "/pictures/file.png?url=https://evil.example", BASE + "/pictures/file.png#fragment",
])
def test_untrusted_url_rejected(url):
    """不允许任意代理、来源伪装、路径穿越及凭据。"""
    with pytest.raises(HTTPException) as error:
        validate_source_url(url, BASE)
    assert error.value.status_code == 422


def test_corrupt_and_unsupported_image():
    """错误 MIME 不能绕过真实内容校验。"""
    for data in [b"not an image", image_bytes("BMP"), image_bytes()[:25]]:
        with pytest.raises(HTTPException) as error:
            inspect_image(data)
        assert error.value.status_code == 415


def test_pixel_limit():
    """在完整解码前拒绝超像素图片。"""
    buffer = BytesIO()
    Image.new("1", (5001, 5000)).save(buffer, "PNG")
    with pytest.raises(HTTPException) as error:
        inspect_image(buffer.getvalue())
    assert error.value.status_code == 413


@pytest.mark.asyncio
async def test_valid_download():
    """上游 MIME 即使错误，也以真实图像格式返回。"""
    data = image_bytes()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=data, headers={"Content-Type": "text/plain"}))
    service = BeadSourceService(transport)
    assert await service.read(URL, BASE) == (data, "image/png")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [301, 302, 404, 500])
async def test_redirect_and_failure(status_code):
    """禁止跟随重定向，外部错误统一映射为 502。"""
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(status_code, headers={"Location": "https://evil.example"})

    with pytest.raises(HTTPException) as error:
        await BeadSourceService(httpx.MockTransport(handler)).read(URL, BASE)
    assert error.value.status_code == 502
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", [True, False])
async def test_byte_limit(declared):
    """缺少 Content-Length 时仍按实际流量执行上限。"""
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            """分块产生超限字节，测试中不请求真实存储。"""
            for _ in range(11):
                yield b"x" * (1024 * 1024)

    headers = {"Content-Length": str(MAX_BYTES + 1)} if declared else {}
    with pytest.raises(HTTPException) as error:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, headers=headers, stream=Stream()))
        await BeadSourceService(transport).read(URL, BASE)
    assert error.value.status_code == 413


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type,code", [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)])
async def test_network_errors(error_type, code):
    """网络故障提供可恢复提示，不返回内部 URL。"""
    def handler(request):
        raise error_type("private details", request=request)

    with pytest.raises(HTTPException) as error:
        await BeadSourceService(httpx.MockTransport(handler)).read(URL, BASE)
    assert error.value.status_code == code
    assert "private details" not in error.value.detail
