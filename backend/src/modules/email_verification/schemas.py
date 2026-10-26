"""邮箱独立输入协议；不接受客户端提交用户归属或认证状态。"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator

from ..user.schemas import UserRead, UserRegister


def normalize_email(value: str) -> str:
    """产品邮箱标识不区分大小写，保留标准验证后的规范形式。"""
    result = str(TypeAdapter(EmailStr).validate_python(value.strip())).lower()
    if len(result) > 254:
        raise ValueError("邮箱地址最长254字符")
    return result


class BindingRequest(BaseModel):
    """新绑定与换绑使用同一申请协议。"""

    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    _email = field_validator("email")(normalize_email)


class Confirmation(BaseModel):
    """验证码类型在业务层检查，避免全局参数错误日志把验证码明文记录下来。"""

    model_config = ConfigDict(extra="ignore")
    request_id: UUID
    code: str = Field(repr=False)


class EmailRegistrationRequest(UserRegister):
    """仅扩展可选邮箱，不复制或更改原密码与账号校验。"""

    email: str | None = Field(default=None, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        """空白邮箱视为未填写。"""
        return normalize_email(value) if value and value.strip() else None


class EmailRegistrationResponse(UserRead):
    """旧字段继续保留，额外信息仅供后续邮箱前端对接。"""

    email_verification: dict | None = None


class PublicUserRead(BaseModel):
    """公开个人名片不返回邮箱、第三方认证和内部权限信息。"""

    id: int
    username: str
    name: str
    profile_image_url: str
    user_profile: str | None = None
