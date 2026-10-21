/** 邮箱协议与后端现有接口保持一致，不在客户端伪造投递或认证结果。 */
import type { UserRead } from '@/types/user'

export type DeliveryStatus = 'pending' | 'publishing' | 'queued' | 'processing' | 'sent' | 'failed' | 'cancelled'

export interface EmailRequestAck {
  request_id: string
  expires_at: string
  retry_after: number
  delivery_status: DeliveryStatus
}

export interface EmailPending extends EmailRequestAck {
  email: string
  purpose: 'binding' | 'unbind'
}

export interface EmailStatus {
  email: string | null
  email_verified: boolean
  pending: EmailPending | null
}

export interface EmailConfirmation {
  email: string | null
  email_verified: boolean
}

export interface EmailRegistrationResult extends UserRead {
  email_verification?: EmailRequestAck | null
}
