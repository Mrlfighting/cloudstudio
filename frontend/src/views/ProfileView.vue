<script setup lang="ts">
/** 个人中心：账号身份、资料完整度和常用工作台入口。 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Key, Medal, User } from '@element-plus/icons-vue'
import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import RoleTag from '@/components/RoleTag.vue'
import StatCard from '@/components/StatCard.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import EmptyValue from '@/components/EmptyValue.vue'

const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)

const loginMethod = computed(() => {
  const provider = user.value?.oauth_provider
  if (provider === 'google') return 'Google'
  if (provider === 'github') return 'GitHub'
  return '密码'
})

const tierLabel = computed(() => (user.value?.tier_id ? `Tier ${user.value.tier_id}` : '基础会员'))

const profileCompletion = computed(() => {
  if (!user.value) return 0
  const hasCustomAvatar = Boolean(
    user.value.profile_image_url
      && !user.value.profile_image_url.includes('profileimageurl.com'),
  )
  const checks = [
    Boolean(user.value.name),
    Boolean(user.value.email),
    hasCustomAvatar,
    Boolean(user.value.user_profile),
    user.value.email_verified,
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
})

const workspaceLinks = [
  { title: '我的空间', desc: '管理私藏图片与容量', icon: 'FolderOpened', path: '/spaces', tone: 'sky' },
  { title: '颜色搜图', desc: '按主色调寻找素材', icon: 'Brush', path: '/spaces/color-search', tone: 'mint' },
  { title: '数据分析', desc: '查看创作与存储趋势', icon: 'DataAnalysis', path: '/analytics/my-space', tone: 'lavender' },
] as const

onMounted(async () => {
  if (!auth.user) {
    try {
      const me = await userApi.getMe()
      auth.setUser(me)
    } catch {
      ElMessage.error('获取用户信息失败')
    }
  }
})
</script>

<template>
  <main class="profile-page page-container">
    <span class="profile-orb profile-orb--blue" aria-hidden="true"></span>
    <span class="profile-orb profile-orb--pink" aria-hidden="true"></span>

    <el-skeleton v-if="!user" :rows="8" animated />

    <template v-else>
      <section class="profile-hero analytics-reveal">
        <div class="profile-hero__pattern" aria-hidden="true">
          <i v-for="index in 18" :key="index"></i>
        </div>
        <div class="profile-hero__content">
          <div class="avatar-shell">
            <UserAvatar :user="user" :size="96" />
            <span class="online-badge" title="账号状态正常"></span>
          </div>
          <div class="profile-identity">
            <div class="profile-kicker">PROFILE · 创作身份</div>
            <div class="profile-name-row">
              <h1>{{ user.name }}</h1>
              <RoleTag :role="user.user_role" />
            </div>
            <p>@{{ user.username }}</p>
            <div class="identity-chips">
              <span><el-icon><Connection /></el-icon>{{ loginMethod }}登录</span>
              <span :class="{ verified: user.email_verified }">
                <el-icon><CircleCheck /></el-icon>{{ user.email_verified ? '邮箱已认证' : '邮箱待认证' }}
              </span>
              <span><el-icon><Medal /></el-icon>{{ tierLabel }}</span>
            </div>
          </div>
        </div>
        <el-button type="primary" size="large" @click="router.push('/profile/edit')">
          <el-icon><Edit /></el-icon>编辑资料
        </el-button>
      </section>

      <section class="profile-stat-grid" aria-label="账号概览">
        <StatCard label="账号 ID" :value="user.id" description="你的平台身份编号" :icon="User" :delay="80" />
        <StatCard label="注册方式" :value="loginMethod" description="当前账号登录凭据" :icon="Key" accent="sky" :delay="140" />
        <StatCard label="邮箱状态" :value="user.email_verified ? '已认证' : '未认证'" description="用于账号安全与通知" :icon="CircleCheckFilled" accent="mint" :delay="200" />
        <StatCard label="会员等级" :value="tierLabel" description="当前账号服务等级" :icon="Medal" accent="lavender" :delay="260" />
      </section>

      <section class="profile-content-grid">
        <article class="profile-panel profile-details analytics-reveal" style="--reveal-delay: 320ms">
          <header class="profile-panel__head">
            <div><h2>身份档案</h2><p>你的公开资料与账号信息</p></div>
            <span class="status-pill"><i></i>账号正常</span>
          </header>

          <div class="detail-list">
            <div class="detail-row">
              <span class="detail-icon detail-icon--rose"><el-icon><User /></el-icon></span>
              <div><small>用户名</small><strong>{{ user.username }}</strong></div>
            </div>
            <div class="detail-row">
              <span class="detail-icon detail-icon--sky"><el-icon><Message /></el-icon></span>
              <div><small>邮箱地址</small><strong><EmptyValue :value="user.email" /></strong></div>
            </div>
            <div class="detail-row detail-row--bio">
              <span class="detail-icon detail-icon--mint"><el-icon><ChatLineSquare /></el-icon></span>
              <div><small>个人简介</small><strong><EmptyValue :value="user.user_profile" /></strong></div>
            </div>
            <div class="detail-row">
              <span class="detail-icon detail-icon--lavender"><el-icon><Avatar /></el-icon></span>
              <div><small>账号角色</small><strong><RoleTag :role="user.user_role" /></strong></div>
            </div>
          </div>
        </article>

        <aside class="profile-side-stack">
          <article class="profile-panel completion-panel analytics-reveal" style="--reveal-delay: 380ms">
            <header class="profile-panel__head"><div><h2>资料完整度</h2><p>完善身份，让协作更高效</p></div></header>
            <div class="completion-body">
              <el-progress
                type="dashboard"
                :percentage="profileCompletion"
                :width="132"
                :stroke-width="11"
                color="#ec7296"
              />
              <div class="completion-copy">
                <strong>{{ profileCompletion >= 100 ? '资料已完善' : '继续完善资料' }}</strong>
                <span>{{ profileCompletion >= 100 ? '所有身份信息均已补充' : '补充头像、邮箱或个人简介' }}</span>
                <el-button link type="primary" @click="router.push('/profile/edit')">去完善 <el-icon><ArrowRight /></el-icon></el-button>
              </div>
            </div>
          </article>

          <article class="profile-panel workspace-panel analytics-reveal" style="--reveal-delay: 440ms">
            <header class="profile-panel__head"><div><h2>创作工作台</h2><p>快速进入常用功能</p></div></header>
            <div class="workspace-links">
              <button v-for="item in workspaceLinks" :key="item.path" @click="router.push(item.path)">
                <span class="workspace-icon" :class="`workspace-icon--${item.tone}`">
                  <el-icon><component :is="item.icon" /></el-icon>
                </span>
                <span><strong>{{ item.title }}</strong><small>{{ item.desc }}</small></span>
                <el-icon class="workspace-arrow"><ArrowRight /></el-icon>
              </button>
            </div>
          </article>
        </aside>
      </section>
    </template>
  </main>
</template>

<style scoped>
.profile-page { position: relative; isolation: isolate; overflow: hidden; padding-bottom: 70px; }
.profile-page::before { content: ''; position: absolute; z-index: -2; inset: 0 0 auto; height: 560px; background: radial-gradient(circle at 8% 10%, rgba(159,220,244,.34), transparent 30%), radial-gradient(circle at 90% 8%, rgba(249,175,197,.28), transparent 30%); pointer-events: none; }
.profile-orb { position: absolute; z-index: -1; border-radius: 50%; pointer-events: none; animation: profile-drift 8s ease-in-out infinite alternate; }
.profile-orb--blue { width: 190px; height: 190px; left: -100px; top: 550px; background: rgba(159,220,244,.18); }
.profile-orb--pink { width: 260px; height: 260px; right: -140px; top: 780px; background: rgba(236,114,150,.13); animation-delay: -3s; }

.profile-hero { position: relative; z-index: 1; min-height: 270px; display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 18px; padding: 44px clamp(26px, 4vw, 54px); overflow: hidden; border: 1px solid rgba(255,255,255,.86); border-radius: 30px; background: linear-gradient(125deg, rgba(213,241,251,.96), rgba(255,255,255,.94) 50%, rgba(255,226,235,.94)); box-shadow: 0 24px 62px rgba(42,47,59,.1); }
.profile-hero::before { content: ''; position: absolute; width: 260px; height: 260px; right: 16%; top: -180px; border-radius: 50%; background: rgba(255,255,255,.48); box-shadow: 0 0 0 45px rgba(255,255,255,.16); }
.profile-hero__pattern { position: absolute; inset: 0 0 0 56%; display: grid; grid-template-columns: repeat(6, 9px); align-content: center; justify-content: center; gap: 18px; opacity: .38; transform: rotate(-8deg); }
.profile-hero__pattern i { width: 9px; height: 9px; border-radius: 3px; background: #e17a9a; animation: profile-pixel 2.8s ease-in-out infinite alternate; }
.profile-hero__pattern i:nth-child(3n) { background: #75cce9; animation-delay: -.8s; }
.profile-hero__pattern i:nth-child(4n) { background: #8bd5c3; animation-delay: -1.4s; }
.profile-hero__content { position: relative; z-index: 1; display: flex; align-items: center; gap: 24px; min-width: 0; }
.avatar-shell { position: relative; flex-shrink: 0; padding: 6px; border-radius: 50%; background: rgba(255,255,255,.86); box-shadow: 0 17px 38px rgba(52,58,70,.16); }
.avatar-shell :deep(.el-avatar) { border: 4px solid #fff; background: linear-gradient(145deg, #82cfe9, #ed789a); color: #fff; font-size: 34px; font-weight: 900; }
.online-badge { position: absolute; right: 9px; bottom: 10px; width: 18px; height: 18px; border: 4px solid #fff; border-radius: 50%; background: #58c3a6; box-shadow: 0 0 0 4px rgba(88,195,166,.14); }
.profile-kicker { margin-bottom: 8px; color: #a9677b; font-size: 10px; font-weight: 900; letter-spacing: 2px; }
.profile-name-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.profile-name-row h1 { margin: 0; color: #1d2128; font-size: clamp(32px, 4vw, 50px); line-height: 1.1; font-weight: 950; letter-spacing: -2px; }
.profile-identity > p { margin: 5px 0 0; color: #75808d; font-size: 14px; font-weight: 700; }
.identity-chips { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.identity-chips span { display: inline-flex; align-items: center; gap: 6px; min-height: 30px; padding: 0 11px; border: 1px solid rgba(255,255,255,.9); border-radius: 999px; color: #697380; background: rgba(255,255,255,.62); font-size: 11px; font-weight: 700; backdrop-filter: blur(10px); }
.identity-chips span.verified { color: #368d75; background: rgba(235,250,246,.8); }
.profile-hero > .el-button { position: relative; z-index: 1; min-width: 128px; height: 46px; }

.profile-stat-grid { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 16px; margin-bottom: 18px; }
.profile-content-grid { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(330px, .65fr); gap: 18px; align-items: start; }
.profile-panel { min-width: 0; padding: 24px; border: 1px solid rgba(224,228,236,.92); border-radius: 23px; background: rgba(255,255,255,.9); box-shadow: 0 14px 38px rgba(39,45,58,.065); backdrop-filter: blur(16px); transition: transform .3s ease, box-shadow .3s ease; }
.profile-panel:hover { transform: translateY(-4px); box-shadow: 0 22px 50px rgba(39,45,58,.1); }
.profile-panel__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 20px; }
.profile-panel__head h2 { margin: 0; color: #292e37; font-size: 17px; font-weight: 900; }
.profile-panel__head p { margin: 6px 0 0; color: #9aa3ae; font-size: 11px; }
.status-pill { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border-radius: 999px; color: #378c75; background: #eaf8f4; font-size: 11px; font-weight: 800; }
.status-pill i { width: 6px; height: 6px; border-radius: 50%; background: #51b99d; box-shadow: 0 0 0 5px rgba(81,185,157,.12); }
.detail-list { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-row { display: flex; align-items: center; gap: 13px; min-width: 0; padding: 16px; border: 1px solid #eff1f5; border-radius: 17px; background: linear-gradient(145deg, #fbfcfe, #fff); }
.detail-row--bio { align-items: flex-start; grid-column: 1 / -1; }
.detail-icon { width: 40px; height: 40px; display: grid; place-items: center; flex-shrink: 0; border-radius: 13px; color: #e36d91; background: #fff0f5; }
.detail-icon--sky { color: #54b9df; background: #eaf9ff; }
.detail-icon--mint { color: #56b89f; background: #e9faf6; }
.detail-icon--lavender { color: #8e7bd3; background: #f1edff; }
.detail-row > div { min-width: 0; }
.detail-row small, .detail-row strong { display: block; }
.detail-row small { margin-bottom: 6px; color: #9ca4af; font-size: 11px; font-weight: 700; }
.detail-row strong { overflow-wrap: anywhere; color: #373d47; font-size: 14px; line-height: 1.7; font-weight: 800; }
.profile-side-stack { display: grid; gap: 18px; }
.completion-body { display: flex; align-items: center; gap: 22px; }
.completion-panel :deep(.el-progress__text) { color: #282d35 !important; font-size: 23px !important; font-weight: 900; }
.completion-copy { min-width: 0; }
.completion-copy strong, .completion-copy span { display: block; }
.completion-copy strong { color: #343a44; font-size: 15px; font-weight: 900; }
.completion-copy span { margin-top: 7px; color: #99a1ac; font-size: 11px; line-height: 1.6; }
.completion-copy .el-button { margin-top: 7px; padding: 0; }
.workspace-links { display: grid; gap: 9px; }
.workspace-links button { display: flex; align-items: center; gap: 12px; width: 100%; padding: 11px; border: 1px solid transparent; border-radius: 15px; background: #fafbfd; text-align: left; cursor: pointer; transition: transform .24s ease, border-color .24s ease, background .24s ease; }
.workspace-links button:hover { transform: translateX(5px); border-color: #f1d1db; background: #fff8fa; }
.workspace-icon { width: 39px; height: 39px; display: grid; place-items: center; flex-shrink: 0; border-radius: 13px; color: #d95f84; background: #fff0f5; }
.workspace-icon--sky { color: #54b9df; background: #eaf9ff; }
.workspace-icon--mint { color: #56b89f; background: #e9faf6; }
.workspace-icon--lavender { color: #8e7bd3; background: #f1edff; }
.workspace-links button > span:nth-child(2) { min-width: 0; flex: 1; }
.workspace-links strong, .workspace-links small { display: block; }
.workspace-links strong { color: #3b414b; font-size: 13px; font-weight: 800; }
.workspace-links small { margin-top: 4px; color: #a0a8b3; font-size: 10px; }
.workspace-arrow { color: #afb6bf; }

@keyframes profile-drift { to { transform: translate(32px,-24px) scale(1.1); } }
@keyframes profile-pixel { to { transform: translateY(-8px) rotate(8deg); opacity: .55; } }
@media (max-width: 1080px) {
  .profile-stat-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .profile-content-grid { grid-template-columns: 1fr; }
  .profile-side-stack { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .profile-page { padding-left: 16px; padding-right: 16px; }
  .profile-hero { align-items: flex-start; flex-direction: column; padding: 30px 24px; }
  .profile-hero__content { align-items: flex-start; flex-direction: column; }
  .profile-hero > .el-button { width: 100%; }
  .profile-stat-grid, .detail-list, .profile-side-stack { grid-template-columns: 1fr; }
  .detail-row--bio { grid-column: auto; }
}
@media (prefers-reduced-motion: reduce) {
  .profile-orb, .profile-hero__pattern i { animation: none; }
  .profile-panel, .workspace-links button { transition: none; }
  .profile-panel:hover, .workspace-links button:hover { transform: none; }
}
</style>
