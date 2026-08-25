"""图库分析二级缓存：TTL 常量与 key 前缀。

缓存 key 由 ``@cached`` 装饰器的默认 key 构造器按 ``key_prefix + 标量参数`` 自动拼接
（``self``/``db`` 自动跳过），因此这里无需手写 key 构造器，只需定义 TTL 与 key 前缀。
"""

# 分析指标变化不频繁，统一 5 分钟缓存（符合 5-10 分钟要求）
ANALYTICS_TTL = 300
