import 'axios'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 公共请求收到 401 时不触发登录弹窗。 */
    skipAuthPrompt?: boolean
    /** 防止登录后重放仍返回 401 时循环。 */
    _authRetried?: boolean
  }

  interface InternalAxiosRequestConfig {
    skipAuthPrompt?: boolean
    _authRetried?: boolean
  }
}

export {}
