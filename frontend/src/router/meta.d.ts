import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面标题 */
    title?: string
    /** 需要登录 */
    requiresAuth?: boolean
    /** 需要管理员权限 */
    requiresAdmin?: boolean
    /** 仅未登录可访问（登录/注册页） */
    guestOnly?: boolean
  }
}

export {}
