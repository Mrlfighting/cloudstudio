/**
 * Cookie 工具（用于读取 JS 可读的 csrf_token 等）
 */

export function getCookie(name: string): string | null {
  const match = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${name}=`))
  if (!match) return null
  return decodeURIComponent(match.slice(name.length + 1))
}

export function setCookie(name: string, value: string, days = 1, path = '/'): void {
  const expires = new Date(Date.now() + days * 86400_000).toUTCString()
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=${path}`
}

export function deleteCookie(name: string, path = '/'): void {
  document.cookie = `${name}=; Max-Age=-1; path=${path}`
}
