/** 独立错误类型使原页面能展示验证原因，无需改变其业务错误处理。 */
export class EmailAccessError extends Error {
  readonly code = 'EMAIL_VERIFICATION_REQUIRED'
  constructor(message = '请先验证邮箱，再使用此功能') {
    super(message)
    this.name = 'EmailAccessError'
  }
}

export class EmailSessionError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'EmailSessionError'
  }
}
