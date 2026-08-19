"""方法级缓存装饰器（二级缓存切面，用于 service 层，与业务解耦）。"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from .two_level import get_cache_manager

T = TypeVar("T", bound=Callable[..., Any])
TTL = int | Callable[..., int]


def cached(
    key_prefix: str,
    ttl: TTL = 300,
    key_builder: Callable[..., str] | None = None,
    track_hot: bool = False,
) -> Callable[[T], T]:
    """二级缓存方法装饰器。

    命中则直接返回缓存；未命中执行原方法并由 ``get_or_load`` 回填两级缓存。
    缓存管理器未初始化或关闭时直接执行原方法（fail-open）。

    注意：Redis 不可用等降级由 ``TwoLevelCacheManager`` 内部处理（吞异常并直读），
    因此业务方法抛出的异常（如 PictureNotFoundError）会原样向上传播，不会被误吞。

    Args:
        key_prefix: 缓存 key 前缀。
        ttl: L2 过期时间（秒）。
        key_builder: 可选的 key 构造器，签名需与原方法一致（含 self/db，内部忽略）。
                     缺省用 key_prefix + 按参数名拼接。
        track_hot: 是否对该 key 做热key探测（详情类接口用）。
    """

    def wrapper(func: T) -> T:
        @functools.wraps(func)
        async def inner(*args: Any, **kwargs: Any) -> Any:
            manager = get_cache_manager()
            if manager is None or not manager.enabled:
                return await func(*args, **kwargs)

            if key_builder is not None:
                key = key_builder(*args, **kwargs)
            else:
                key = _default_key(key_prefix, args, kwargs)

            async def loader() -> Any:
                return await func(*args, **kwargs)

            effective_ttl = ttl(*args, **kwargs) if callable(ttl) else ttl
            return await manager.get_or_load(key, loader, effective_ttl, track_hot=track_hot)

        return inner  # type: ignore[return-value]

    return wrapper


def _default_key(key_prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    parts: list[str] = []
    for arg in args:
        if _is_cacheable(arg):
            parts.append(str(arg))
    for name in sorted(kwargs):
        value = kwargs[name]
        if name in ("db",) or not _is_cacheable(value):
            continue
        parts.append(f"{name}={value}")
    return f"{key_prefix}:" + ":".join(parts)


def _is_cacheable(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None)))
