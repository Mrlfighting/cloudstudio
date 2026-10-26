<script setup lang="ts">
/** 个人中心及编辑资料共用的邮箱入口，不通过资料PATCH修改邮箱。 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useEmailVerificationStore } from './store'

defineProps<{ compact?: boolean }>()
const auth = useAuthStore()
const email = useEmailVerificationStore()
const bound = computed(() => email.status?.email ?? auth.user?.email)
const verified = computed(() => email.checked ? email.canUsePrivate : !!auth.user?.email_verified)
const label = computed(() => email.statusError ? '状态待更新' : verified.value ? '已验证' : bound.value ? '待验证' : '未绑定')
const action = computed(() => verified.value ? '更换邮箱' : email.pending ? '继续验证' : '绑定并验证')
</script>

<template>
  <section class="email-settings-card" :class="{ 'is-compact': compact }" aria-label="邮箱管理">
    <span class="email-card-orb" aria-hidden="true"></span>
    <div class="email-card-top">
      <span class="email-card-icon"><el-icon><Message /></el-icon></span>
      <div class="email-card-copy"><small>ACCOUNT SECURITY</small><h3>邮箱管理 <span :class="{ verified }">{{ label }}</span></h3></div>
    </div>
    <div class="email-card-bottom">
      <div class="email-card-detail">
        <strong>{{ bound || '还没有绑定邮箱' }}</strong>
        <p v-if="email.statusError">{{ email.statusError }}</p>
        <p v-else-if="email.pending">{{ email.pending.email === bound ? '验证申请进行中，可继续输入验证码。' : `新邮箱 ${email.pending.email} 正在等待验证，原邮箱继续有效。` }}</p>
        <p v-else>{{ verified ? '已完成邮箱验证，可使用完整的创作与协作功能。' : '验证常用邮箱后，即可上传、下载和使用私有空间等功能。' }}</p>
      </div>
      <el-button type="primary" plain :loading="email.syncing && !email.visible" @click="email.openSettings(verified && !email.pending)">{{ email.pending ? '继续验证' : action }}<el-icon><ArrowRight /></el-icon></el-button>
    </div>
  </section>
</template>

<style scoped>
.email-settings-card { position: relative; isolation: isolate; overflow: hidden; margin-bottom: 18px; padding: 25px 28px; border: 1px solid #dfeaf1; border-radius: 24px; background: linear-gradient(118deg,#eef9fe,#fff 53%,#fff1f6); box-shadow: 0 12px 35px rgba(61,88,119,.06); }
.email-card-orb { position: absolute; z-index: -1; right: -55px; top: -75px; width: 205px; height: 205px; border: 30px solid rgba(237,171,197,.1); border-radius: 50%; pointer-events: none; }
.email-card-top { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.email-card-icon { display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 15px; color: #b47d99; background: linear-gradient(145deg,#fff,#f5dfe9); box-shadow: inset 0 0 0 1px rgba(255,255,255,.9); font-size: 23px; }
.email-card-copy small { color: #a6a0b0; font-size: 9px; font-weight: 800; letter-spacing: 1.8px; }
.email-card-copy h3 { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; margin: 5px 0 0; color: #333e4d; font-size: 17px; }
.email-card-copy h3 span { padding: 3px 8px; border-radius: 999px; background: #fae7ef; color: #b7768e; font-size: 10px; }
.email-card-copy h3 .verified { color: #388e74; background: #e2f4ec; }
.email-card-bottom { display: flex; align-items: center; justify-content: space-between; gap: 22px; }
.email-card-detail { min-width: 0; }
.email-card-detail strong { display: block; color: #536175; font-size: 16px; overflow-wrap: anywhere; }
.email-card-detail p { margin: 7px 0 0; color: #8c97a5; font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.email-card-bottom .el-button { flex-shrink: 0; height: 40px; }
.email-card-bottom .el-icon { margin-left: 6px; }
.is-compact { padding: 17px; margin: 0; border-radius: 17px; width: 100%; box-sizing: border-box; }
.is-compact .email-card-top { margin-bottom: 12px; }
.is-compact .email-card-bottom { align-items: flex-start; flex-direction: column; gap: 12px; }
.is-compact .email-card-detail strong { font-size: 13px; }
@media(max-width:560px) { .email-settings-card { padding: 20px; border-radius: 20px; } .email-card-bottom { align-items: stretch; flex-direction: column; gap: 16px; } .email-card-detail strong { font-size: 14px; } .is-compact { padding: 15px; } }
</style>
