<script setup lang="ts">
/** 全局验证码弹窗：仅在真实投递成功后显示“已发送”，关闭后清除敏感输入。 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useEmailVerificationStore } from './store'

const email = useEmailVerificationStore()
const formRef = ref<FormInstance>()
const now = ref(Date.now())
const pageVisible = ref(document.visibilityState !== 'hidden')
let tick: ReturnType<typeof setInterval> | undefined
let poll: ReturnType<typeof setTimeout> | undefined
const remaining = computed(() => Math.max(0, Math.ceil((email.retryAt - now.value) / 1000)))
const confirmRemaining = computed(() => Math.max(0, Math.ceil((email.confirmRetryAt - now.value) / 1000)))
const expired = computed(() => !!email.pending && Date.parse(email.pending.expires_at) <= now.value)
const isEditing = computed(() => email.editing || !email.pending)
const deliveryActive = computed(() => !!email.pending && !expired.value
  && ['pending', 'publishing', 'queued', 'processing'].includes(email.pending.delivery_status))
const statusText = computed(() => {
  if (!email.pending) return '验证邮箱，让创作与协作更安心'
  if (expired.value) return '验证码已过期，请重新申请'
  if (email.pending.delivery_status === 'sent') return '验证邮件已发送，请查收'
  if (email.pending.delivery_status === 'failed') return '邮件发送失败，请稍后重新发送'
  if (email.pending.delivery_status === 'cancelled') return '此次发送已取消，请重新申请'
  return '邮件正在发送中，请稍候'
})
const rules: FormRules = {
  address: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
    { max: 254, message: '邮箱地址最长254个字符', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入邮件中的验证码', trigger: 'blur' },
    { pattern: /^[0-9]{6}$/, message: '请输入6位数字验证码', trigger: 'blur' },
  ],
}

function stopTimers(): void {
  clearInterval(tick)
  clearTimeout(poll)
}
function schedule(): void {
  stopTimers()
  now.value = Date.now()
  if (!email.visible || !pageVisible.value) return
  tick = setInterval(() => { now.value = Date.now() }, 1000)
  if (deliveryActive.value) {
    poll = setTimeout(async () => {
      if (email.visible && pageVisible.value) await email.refresh()
      schedule()
    }, 3000)
  }
}
watch(() => [email.visible, email.pending?.request_id, email.pending?.delivery_status, pageVisible.value], schedule)
watch(expired, (value) => { if (value && email.visible) { schedule(); void email.refresh() } })
watch(() => email.pending?.request_id, (id, old) => {
  if (old && !id && email.visible && !email.canUsePrivate) {
    email.code = ''
    email.formError = '验证申请已结束或过期，请重新获取验证码'
  }
})
function visibilityChanged(): void {
  pageVisible.value = document.visibilityState !== 'hidden'
  now.value = Date.now()
}
onMounted(() => { document.addEventListener('visibilitychange', visibilityChanged); schedule() })
onBeforeUnmount(() => { stopTimers(); document.removeEventListener('visibilitychange', visibilityChanged) })

async function send(): Promise<void> {
  const valid = await formRef.value?.validateField('address').then(() => true).catch(() => false)
  if (!valid) return
  if (await email.sendCode()) ElMessage.info('验证申请已受理，正在发送邮件')
}
async function resend(): Promise<void> {
  if (email.pending) email.address = email.pending.email
  if (await email.sendCode()) ElMessage.info('新的验证申请已受理，旧验证码已失效')
}
async function confirm(): Promise<void> {
  const valid = await formRef.value?.validateField('code').then(() => true).catch(() => false)
  if (!valid || expired.value) return
  if (await email.confirmCode()) ElMessage.success('邮箱验证成功')
}
function close(visible: boolean): void {
  if (!visible && email.visible) email.defer()
}
</script>

<template>
  <el-dialog
    :model-value="email.visible" width="min(500px, calc(100vw - 28px))"
    class="email-verification-dialog" append-to-body align-center destroy-on-close
    :close-on-click-modal="false" @update:model-value="close"
  >
    <template #header>
      <div class="email-dialog-heading">
        <span class="email-dialog-mark"><el-icon><Message /></el-icon></span>
        <div><span class="email-eyebrow">ACCOUNT · 邮箱安全</span><h2>{{ email.canUsePrivate ? '更换绑定邮箱' : '验证你的邮箱' }}</h2></div>
      </div>
    </template>
    <div class="email-dialog-body">
      <p class="email-dialog-reason">{{ email.reason }}</p>
      <div class="email-steps" aria-label="邮箱验证步骤">
        <span :class="{ active: isEditing }"><i>1</i>填写邮箱</span>
        <b></b><span :class="{ active: !isEditing }"><i>2</i>输入验证码</span>
        <b></b><span><i>3</i>验证完成</span>
      </div>
      <el-alert v-if="email.statusError" :title="email.statusError" type="warning" show-icon :closable="false" />
      <el-button v-if="email.statusError" class="email-retry-status" :loading="email.syncing" @click="email.refresh()">重新获取邮箱状态</el-button>

      <div v-if="!isEditing && email.pending" class="email-delivery" :class="`is-${email.pending.delivery_status}`" aria-live="polite">
        <span class="email-delivery-icon"><el-icon><component :is="email.pending.delivery_status === 'sent' ? 'CircleCheck' : 'Message'" /></el-icon></span>
        <div><strong>{{ statusText }}</strong><p>{{ email.pending.email }}</p>
          <small v-if="email.pending.delivery_status === 'sent' && !expired">请输入邮件中的6位验证码，有效期以当前验证申请为准。</small>
          <small v-else-if="deliveryActive">已登记发送任务，投递完成后会自动更新状态。</small>
          <small v-else>可检查垃圾箱，或在冷却结束后重新发送。</small>
        </div>
      </div>

      <el-form ref="formRef" :model="email" :rules="rules" label-position="top" @submit.prevent="isEditing ? send() : confirm()">
        <template v-if="isEditing">
          <el-form-item label="邮箱地址" prop="address">
            <el-input v-model.trim="email.address" placeholder="请输入常用邮箱" maxlength="254" type="email" autocomplete="email" inputmode="email" clearable>
              <template #prefix><el-icon><Message /></el-icon></template>
            </el-input>
          </el-form-item>
          <p v-if="email.canUsePrivate" class="email-form-note">新邮箱验证成功前，当前绑定邮箱继续有效。</p>
          <el-button native-type="submit" type="primary" class="email-primary-action" :loading="email.sending" :disabled="remaining > 0">
            {{ remaining ? `${remaining}秒后可发送` : '发送验证邮件' }}
          </el-button>
          <el-button v-if="email.pending" link class="email-return-code" @click="email.resumePending()">返回当前验证码申请</el-button>
        </template>
        <template v-else>
          <el-form-item label="邮件验证码" prop="code">
            <el-input :model-value="email.code" maxlength="6" inputmode="numeric" autocomplete="one-time-code" placeholder="请输入6位数字验证码" class="email-code-input"
              @update:model-value="email.code = String($event).replace(/[^0-9]/g, '').slice(0, 6)" />
          </el-form-item>
          <div class="email-code-tools">
            <el-button link type="primary" :loading="email.sending" :disabled="remaining > 0" @click="resend">{{ remaining ? `${remaining}秒后可重发` : '重新发送验证码' }}</el-button>
            <el-button link @click="email.editAddress()">更换接收邮箱</el-button>
          </div>
          <el-button native-type="submit" type="primary" class="email-primary-action" :loading="email.confirming"
            :disabled="expired || email.sending || confirmRemaining > 0 || !/^[0-9]{6}$/.test(email.code)">
            {{ confirmRemaining ? `${confirmRemaining}秒后可重试` : '确认验证邮箱' }}
          </el-button>
        </template>
      </el-form>
      <el-alert v-if="email.formError" :title="email.formError" type="error" show-icon :closable="false" class="email-form-error" />
      <div class="email-dialog-footer">
        <span><el-icon><Lock /></el-icon>验证码仅用于验证当前账号的邮箱</span>
        <el-button link @click="email.defer()">暂缓验证，继续浏览</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<style>
.email-verification-dialog { display: flex; flex-direction: column; align-self: center; height: fit-content; max-height: calc(100dvh - 24px); overflow: hidden; border: 1px solid rgba(255,255,255,.94); border-radius: 26px; background: linear-gradient(145deg,#f0faff 0%,#fff 43%,#fff2f6 100%); box-shadow: 0 28px 95px rgba(63,77,111,.2); }
.email-verification-dialog .el-dialog__header { padding: 26px 28px 8px; margin: 0; }
.email-verification-dialog .el-dialog__body { min-height: 0; overflow-y: auto; padding: 8px 28px 26px; }
.email-dialog-heading { display: flex; gap: 14px; align-items: center; padding-right: 20px; }
.email-dialog-mark { display: grid; place-items: center; width: 52px; height: 52px; flex: 0 0 52px; border: 1px solid #fff; border-radius: 17px; color: #fff; background: linear-gradient(135deg,#7bcee6,#b2aae8 53%,#ee94ae); box-shadow: 0 10px 24px rgba(145,155,207,.25); font-size: 26px; transform: rotate(-5deg); }
.email-eyebrow { color: #ac7083; font-size: 10px; font-weight: 800; letter-spacing: 1.8px; }
.email-dialog-heading h2 { margin: 5px 0 0; color: #26313d; font-size: 24px; }
.email-dialog-reason { margin: 6px 0 20px; color: #7c8797; font-size: 13px; line-height: 1.8; }
.email-steps { display: flex; align-items: center; margin-bottom: 24px; gap: 8px; }
.email-steps span { display: inline-flex; align-items: center; gap: 6px; color: #9aa5b0; font-size: 11px; white-space: nowrap; }
.email-steps i { display: grid; place-items: center; width: 23px; height: 23px; border-radius: 50%; background: #edf0f5; font-size: 10px; font-style: normal; }
.email-steps b { flex: 1; height: 1px; background: #e5eaf1; }
.email-steps .active { color: #bd6983; font-weight: 800; }
.email-steps .active i { color: #fff; background: linear-gradient(135deg,#ee87a8,#bd9edb); }
.email-delivery { display: flex; align-items: flex-start; gap: 12px; padding: 17px; margin-bottom: 20px; border: 1px solid #dfeef5; border-radius: 17px; background: rgba(238,248,254,.85); }
.email-delivery-icon { display: grid; place-items: center; width: 34px; height: 34px; flex: 0 0 34px; border-radius: 12px; color: #5ba0b7; background: #dbf0fa; font-size: 20px; }
.email-delivery strong { color: #435768; font-size: 13px; }
.email-delivery p { margin: 6px 0; color: #627385; font-size: 13px; overflow-wrap: anywhere; }
.email-delivery small { display: block; color: #8793a1; font-size: 11px; line-height: 1.7; }
.email-delivery.is-sent { border-color: #d6ece5; background: #effaf5; }
.email-delivery.is-sent .email-delivery-icon { color: #409d7f; background: #d8f0e6; }
.email-delivery.is-failed,.email-delivery.is-cancelled { border-color: #f0dce1; background: #fff3f5; }
.email-primary-action { width: 100%; min-height: 44px; margin-top: 5px; }
.email-code-input .el-input__inner { letter-spacing: 7px; font-size: 21px; font-weight: 700; }
.email-code-input .el-input__inner::placeholder { letter-spacing: 0; font-size: 13px; font-weight: 400; }
.email-code-tools { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px; margin: -4px 0 16px; }
.email-form-note { margin: -4px 0 18px; color: #919baa; font-size: 12px; line-height: 1.8; }
.email-form-error { margin-top: 14px; }
.email-return-code { display: block; margin: 12px auto 0 !important; }
.email-retry-status { margin: 10px 0 18px; }
.email-dialog-footer { display: flex; flex-direction: column; align-items: center; gap: 13px; margin-top: 22px; padding-top: 18px; border-top: 1px solid #e9edf3; }
.email-dialog-footer > span { display: inline-flex; align-items: center; gap: 5px; color: #9aa3b0; font-size: 11px; }
@media(max-width:560px) { .email-verification-dialog .el-dialog__header { padding: 22px 18px 8px; } .email-verification-dialog .el-dialog__body { padding: 8px 18px 20px; } .email-dialog-heading h2 { font-size: 21px; } .email-steps { gap: 5px; } .email-steps span { gap: 4px; font-size: 10px; } .email-delivery { padding: 13px; gap: 9px; } }
</style>
