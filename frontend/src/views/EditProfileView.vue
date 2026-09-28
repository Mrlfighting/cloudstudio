<script setup lang="ts">
/**
 * 编辑资料：PATCH 路径使用编辑前的 username，成功后重新获取用户资料。
 * 页面视觉与实时预览不改变原有字段、校验和接口行为。
 */
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { userApi } from '@/api/user'
import { getErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { UpdateProfilePayload } from '@/types/user'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const avatarFailed = ref(false)

const form = reactive({
  name: '',
  username: '',
  email: '',
  profile_image_url: '',
  user_profile: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 30, message: '昵称长度为 2-30 个字符', trigger: 'blur' },
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-z0-9]{2,20}$/, message: '用户名为 2-20 位小写字母或数字', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  profile_image_url: [
    {
      pattern: /^(https?|ftp):\/\/[^\s/$.?#][^\s]*$/,
      message: '请输入合法的图片地址（http/https/ftp）',
      trigger: 'blur',
    },
  ],
  user_profile: [{ max: 512, message: '简介最长 512 个字符', trigger: 'blur' }],
}

const avatarPreview = computed(() => {
  if (avatarFailed.value || !form.profile_image_url.trim()) return undefined
  return form.profile_image_url.trim()
})

const profileInitial = computed(() => (form.name.trim() || form.username.trim() || 'U').charAt(0).toUpperCase())

const completionPercent = computed(() => {
  const fields = [form.name, form.username, form.email, form.profile_image_url, form.user_profile]
  return Math.round((fields.filter((value) => value.trim()).length / fields.length) * 100)
})

const completionText = computed(() => {
  if (completionPercent.value === 100) return '资料已经很完整'
  if (completionPercent.value >= 60) return '再补充一些信息吧'
  return '完善资料，让大家更了解你'
})

watch(
  () => form.profile_image_url,
  () => { avatarFailed.value = false },
)

function prefill() {
  if (!auth.user) return
  form.name = auth.user.name
  form.username = auth.user.username
  form.email = auth.user.email ?? ''
  form.profile_image_url = auth.user.profile_image_url ?? ''
  form.user_profile = auth.user.user_profile ?? ''
}

async function load() {
  if (!auth.user) {
    const me = await userApi.getMe()
    auth.setUser(me)
  }
  prefill()
}

load()

async function handleSubmit() {
  if (!formRef.value || !auth.user) return
  await formRef.value.validate()

  const payload: UpdateProfilePayload = {
    name: form.name,
    username: form.username,
    email: form.email.trim() ? form.email.trim() : null,
    profile_image_url: form.profile_image_url.trim() ? form.profile_image_url.trim() : null,
    user_profile: form.user_profile.trim() ? form.user_profile.trim() : null,
  }

  const oldUsername = auth.user.username
  loading.value = true
  try {
    await userApi.updateProfile(oldUsername, payload)
    ElMessage.success('资料更新成功')
    const me = await userApi.getMe()
    auth.setUser(me)
    router.push('/profile')
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '资料更新失败，该用户名或邮箱可能已被占用'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="edit-profile-page page-container">
    <section class="profile-hero analytics-reveal">
      <div class="hero-copy">
        <el-button class="profile-back-button" :icon="'ArrowLeft'" round @click="router.push('/profile')">
          返回个人中心
        </el-button>
        <div class="eyebrow">ACCOUNT · 个人资料</div>
        <h1>把你的个人名片<br /><span>装点得更有温度</span></h1>
        <p>更新公开昵称、头像与个人介绍，资料保存后会同步到你的个人中心。</p>
      </div>
      <div class="hero-decoration" aria-hidden="true">
        <div class="pixel-face"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
        <span class="hero-star hero-star--one">✦</span>
        <span class="hero-star hero-star--two">✦</span>
        <span class="hero-ring"></span>
      </div>
    </section>

    <section class="edit-layout">
      <main class="form-panel analytics-reveal" style="--reveal-delay: 100ms">
        <div class="form-panel__heading">
          <div>
            <span>PROFILE SETTINGS</span>
            <h2>编辑资料</h2>
            <p>带有必填标识的内容用于识别你的账号。</p>
          </div>
          <div class="completion-chip">
            <el-icon><CircleCheck /></el-icon>
            完整度 {{ completionPercent }}%
          </div>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="profile-form">
          <section class="form-section">
            <div class="section-heading">
              <span class="section-icon section-icon--rose"><el-icon><User /></el-icon></span>
              <div><h3>身份信息</h3><p>昵称会公开展示，用户名用于识别账号。</p></div>
            </div>
            <div class="field-grid">
              <el-form-item label="昵称" prop="name">
                <el-input v-model="form.name" placeholder="请输入昵称" maxlength="30" show-word-limit>
                  <template #prefix><el-icon><MagicStick /></el-icon></template>
                </el-input>
              </el-form-item>
              <el-form-item label="用户名" prop="username">
                <el-input v-model="form.username" placeholder="2-20 位小写字母或数字" maxlength="20" show-word-limit>
                  <template #prefix><span class="input-prefix">@</span></template>
                </el-input>
              </el-form-item>
            </div>
          </section>

          <section class="form-section">
            <div class="section-heading">
              <span class="section-icon section-icon--sky"><el-icon><Postcard /></el-icon></span>
              <div><h3>联系与头像</h3><p>邮箱和头像均可选填，留空即可清除原内容。</p></div>
            </div>
            <div class="field-grid">
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="form.email" placeholder="name@example.com" clearable>
                  <template #prefix><el-icon><Message /></el-icon></template>
                </el-input>
              </el-form-item>
              <el-form-item label="头像地址" prop="profile_image_url">
                <el-input v-model="form.profile_image_url" placeholder="https://..." clearable>
                  <template #prefix><el-icon><Link /></el-icon></template>
                </el-input>
              </el-form-item>
            </div>
          </section>

          <section class="form-section form-section--bio">
            <div class="section-heading">
              <span class="section-icon section-icon--mint"><el-icon><ChatLineSquare /></el-icon></span>
              <div><h3>个人介绍</h3><p>用一小段话介绍你的兴趣、创作方向或正在做的事情。</p></div>
            </div>
            <el-form-item label="简介" prop="user_profile">
              <el-input
                v-model="form.user_profile"
                type="textarea"
                :rows="5"
                maxlength="512"
                show-word-limit
                resize="none"
                placeholder="介绍一下自己吧……"
              />
            </el-form-item>
          </section>

          <div class="form-actions">
            <div class="save-note"><el-icon><Lock /></el-icon>保存后会重新加载你的最新资料</div>
            <div>
              <el-button size="large" @click="router.push('/profile')">取消</el-button>
              <el-button type="primary" size="large" :loading="loading" @click="handleSubmit">
                <el-icon><Check /></el-icon>
                保存资料
              </el-button>
            </div>
          </div>
        </el-form>
      </main>

      <aside class="preview-column">
        <section class="preview-card analytics-reveal" style="--reveal-delay: 180ms">
          <div class="preview-card__top">
            <span>LIVE PREVIEW</span>
            <i></i>
          </div>
          <div class="preview-cover">
            <span class="cover-shape cover-shape--one"></span>
            <span class="cover-shape cover-shape--two"></span>
            <span class="cover-grid" aria-hidden="true"></span>
          </div>
          <div class="preview-body">
            <div class="avatar-shell">
              <el-avatar :size="92" :src="avatarPreview" @error="avatarFailed = true">{{ profileInitial }}</el-avatar>
              <span class="online-dot"></span>
            </div>
            <el-tag :type="auth.user?.user_role === 'admin' ? 'danger' : 'info'" effect="light" round>
              {{ auth.user?.user_role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
            <h2>{{ form.name || '你的昵称' }}</h2>
            <div class="preview-username">@{{ form.username || 'username' }}</div>
            <p>{{ form.user_profile || '在这里写下你的个人介绍，让大家更了解你。' }}</p>
            <div class="preview-contact" :class="{ 'is-empty': !form.email }">
              <el-icon><Message /></el-icon>
              <span>{{ form.email || '暂未填写邮箱' }}</span>
            </div>
          </div>
        </section>

        <section class="completion-card analytics-reveal" style="--reveal-delay: 260ms">
          <div class="completion-card__header">
            <div><small>资料完整度</small><strong>{{ completionPercent }}%</strong></div>
            <span class="completion-orbit"><i></i></span>
          </div>
          <el-progress :percentage="completionPercent" :stroke-width="9" :show-text="false" color="#ec7296" />
          <p>{{ completionText }}</p>
          <div class="completion-list">
            <span :class="{ complete: form.name.trim() }"><i></i>昵称</span>
            <span :class="{ complete: form.username.trim() }"><i></i>用户名</span>
            <span :class="{ complete: form.email.trim() }"><i></i>邮箱</span>
            <span :class="{ complete: form.profile_image_url.trim() }"><i></i>头像</span>
            <span :class="{ complete: form.user_profile.trim() }"><i></i>简介</span>
          </div>
        </section>

        <section class="tip-card analytics-reveal" style="--reveal-delay: 340ms">
          <span><el-icon><PictureRounded /></el-icon></span>
          <div><strong>头像展示提示</strong><p>头像地址留空或图片不可用时，将使用昵称首字作为头像。</p></div>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.edit-profile-page { position: relative; }
.profile-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 270px; min-height: 280px; margin-bottom: 20px; padding: clamp(30px, 4.5vw, 54px); overflow: hidden; border: 1px solid rgba(255,255,255,.88); border-radius: 30px; background: linear-gradient(120deg, rgba(255,244,248,.97), rgba(239,250,255,.96) 56%, rgba(240,236,255,.93)); box-shadow: 0 24px 70px rgba(69,74,94,.1); }
.profile-hero::before { content: ''; position: absolute; width: 220px; height: 220px; right: 15%; top: -110px; border-radius: 50%; background: rgba(159,220,244,.28); filter: blur(2px); animation: hero-orb 8s ease-in-out infinite; }
.hero-copy { position: relative; z-index: 2; align-self: center; }.profile-back-button { height: 36px; margin: 0 0 24px; padding: 0 15px !important; border-color: rgba(218,183,194,.78) !important; color: #8e5e6d !important; background: rgba(255,255,255,.66) !important; box-shadow: 0 8px 20px rgba(80,72,87,.07); backdrop-filter: blur(10px); transition: color .22s ease, transform .22s ease, box-shadow .22s ease, border-color .22s ease !important; }.profile-back-button:hover, .profile-back-button:focus-visible { color: #bd5576 !important; border-color: #eca7bc !important; background: #fff !important; box-shadow: 0 11px 24px rgba(190,86,119,.13); transform: translateX(-3px); }.profile-back-button:focus-visible { outline: 3px solid rgba(236,114,150,.15); outline-offset: 2px; }.profile-hero h1 { margin: 0; color: #191d24; font-size: clamp(34px, 4vw, 54px); line-height: 1.1; letter-spacing: -2px; font-weight: 900; }.profile-hero h1 span { color: transparent; background: linear-gradient(90deg,#d36788,#758dd8); background-clip: text; -webkit-background-clip: text; }.profile-hero p { max-width: 610px; margin: 18px 0 0; color: #77808d; font-size: 14px; line-height: 1.9; }
.hero-decoration { position: relative; z-index: 2; display: grid; place-items: center; }.pixel-face { display: grid; grid-template-columns: repeat(3, 40px); gap: 7px; padding: 22px; transform: rotate(4deg); border: 1px solid rgba(255,255,255,.9); border-radius: 26px; background: rgba(255,255,255,.6); box-shadow: 0 22px 50px rgba(71,78,99,.12); backdrop-filter: blur(14px); transition: transform .4s cubic-bezier(.22,1,.36,1); }.profile-hero:hover .pixel-face { transform: rotate(0) translateY(-5px); }.pixel-face i { width: 40px; height: 40px; border-radius: 11px; background: #f0a1b9; box-shadow: inset 0 -5px 10px rgba(174,83,111,.08); }.pixel-face i:nth-child(2), .pixel-face i:nth-child(4), .pixel-face i:nth-child(6), .pixel-face i:nth-child(8) { background: #a8ddf1; }.pixel-face i:nth-child(5) { border-radius: 50%; background: #c9bdf2; }.pixel-face i:nth-child(7), .pixel-face i:nth-child(9) { background: #bce7dc; }.hero-star { position: absolute; color: #ec7296; animation: star-float 4s ease-in-out infinite; }.hero-star--one { right: 8px; top: 20px; font-size: 27px; }.hero-star--two { left: 12px; bottom: 19px; color: #76bddc; font-size: 18px; animation-delay: -2s; }.hero-ring { position: absolute; width: 45px; height: 45px; right: 0; bottom: 14px; border: 9px solid rgba(155,137,223,.26); border-radius: 50%; }
.edit-layout { display: grid; grid-template-columns: minmax(0, 1.48fr) minmax(310px, .52fr); gap: 20px; align-items: start; }.form-panel, .preview-card, .completion-card, .tip-card { border: 1px solid rgba(226,229,237,.88); background: rgba(255,255,255,.89); box-shadow: 0 16px 44px rgba(43,48,61,.07); backdrop-filter: blur(16px); }.form-panel { padding: clamp(22px, 3vw, 36px); border-radius: 27px; }.form-panel__heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding-bottom: 24px; border-bottom: 1px solid #f0f1f5; }.form-panel__heading > div:first-child > span { color: #b26880; font-size: 10px; font-weight: 900; letter-spacing: 1.8px; }.form-panel__heading h2 { margin: 7px 0 0; color: #20242b; font-size: 27px; }.form-panel__heading p { margin: 7px 0 0; color: #959da8; font-size: 12px; }.completion-chip { display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto; padding: 8px 12px; border-radius: 999px; color: #bd5f7c; background: #fff0f5; font-size: 11px; font-weight: 800; }
.profile-form { margin-top: 5px; }.form-section { padding: 26px 0 19px; border-bottom: 1px solid #f1f2f5; }.form-section--bio { border-bottom: 0; }.section-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 21px; }.section-icon { display: grid; place-items: center; flex: 0 0 auto; width: 42px; height: 42px; border-radius: 14px; }.section-icon--rose { color: #cf6383; background: #fff0f5; }.section-icon--sky { color: #4eacce; background: #eaf9ff; }.section-icon--mint { color: #4dac96; background: #e9faf6; }.section-heading h3 { margin: 0; color: #30343b; font-size: 15px; }.section-heading p { margin: 5px 0 0; color: #9ba2ac; font-size: 11px; }.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 18px; }.input-prefix { color: #969eaa; font-weight: 800; }
.profile-form :deep(.el-form-item) { margin-bottom: 18px; }.profile-form :deep(.el-form-item__label) { padding-bottom: 8px; color: #5d6570; font-size: 12px; }.profile-form :deep(.el-input__wrapper) { min-height: 44px; padding: 1px 13px; background: #fbfcfe; box-shadow: 0 0 0 1px #e8eaf0 inset !important; transition: background .2s ease, box-shadow .2s ease; }.profile-form :deep(.el-input__wrapper.is-focus) { background: #fff; box-shadow: 0 0 0 1px #ec8ca8 inset, 0 7px 18px rgba(236,114,150,.08) !important; }.profile-form :deep(.el-textarea__inner) { min-height: 130px !important; padding: 14px; background: #fbfcfe; line-height: 1.8; }.form-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-top: 22px; }.form-actions > div:last-child { display: flex; gap: 10px; }.save-note { display: flex; align-items: center; gap: 7px; color: #a0a7b1; font-size: 11px; }.form-actions .el-button .el-icon { margin-right: 6px; }
.preview-column { position: sticky; top: 86px; display: grid; gap: 16px; }.preview-card { overflow: hidden; border-radius: 27px; }.preview-card__top { display: flex; align-items: center; justify-content: space-between; padding: 18px 21px; color: #9b7481; font-size: 10px; font-weight: 900; letter-spacing: 1.7px; }.preview-card__top i { width: 7px; height: 7px; border-radius: 50%; background: #68cdb5; box-shadow: 0 0 0 5px rgba(104,205,181,.14); }.preview-cover { position: relative; height: 112px; overflow: hidden; background: linear-gradient(120deg,#f6c2d2,#bee7f6 58%,#ddd5f8); }.cover-shape { position: absolute; border-radius: 50%; }.cover-shape--one { width: 120px; height: 120px; right: -20px; top: -54px; background: rgba(255,255,255,.36); }.cover-shape--two { width: 75px; height: 75px; left: 18px; bottom: -43px; background: rgba(255,255,255,.3); }.cover-grid { position: absolute; inset: 0; opacity: .3; background-image: linear-gradient(rgba(255,255,255,.75) 1px, transparent 1px), linear-gradient(90deg,rgba(255,255,255,.75) 1px,transparent 1px); background-size: 18px 18px; }
.preview-body { padding: 0 24px 25px; }.avatar-shell { position: relative; width: max-content; margin: -46px 0 12px; padding: 5px; border-radius: 50%; background: #fff; box-shadow: 0 12px 25px rgba(59,65,82,.14); }.avatar-shell :deep(.el-avatar) { color: #fff; background: linear-gradient(135deg,#87cfe9,#e9789a); font-size: 30px; font-weight: 900; }.online-dot { position: absolute; right: 6px; bottom: 10px; width: 16px; height: 16px; border: 3px solid #fff; border-radius: 50%; background: #68cdb5; }.preview-body h2 { margin: 13px 0 0; overflow-wrap: anywhere; color: #22262d; font-size: 23px; line-height: 1.2; }.preview-username { margin-top: 5px; color: #9a8390; font-size: 12px; font-weight: 700; }.preview-body > p { min-height: 45px; margin: 16px 0; color: #7f8792; font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }.preview-contact { display: flex; align-items: center; gap: 8px; padding: 10px 12px; overflow: hidden; border-radius: 12px; color: #697480; background: #f6f8fb; font-size: 11px; }.preview-contact span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.preview-contact.is-empty { color: #a7adb6; }
.completion-card { padding: 21px; border-radius: 22px; }.completion-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }.completion-card__header small, .completion-card__header strong { display: block; }.completion-card__header small { color: #969eaa; font-size: 11px; }.completion-card__header strong { margin-top: 4px; color: #252a31; font-size: 26px; }.completion-orbit { position: relative; width: 42px; height: 42px; border: 1px dashed #e9a1b6; border-radius: 50%; animation: orbit-spin 8s linear infinite; }.completion-orbit i { position: absolute; width: 8px; height: 8px; left: 2px; top: 2px; border-radius: 50%; background: #ec7296; box-shadow: 0 0 0 5px rgba(236,114,150,.12); }.completion-card > p { margin: 12px 0 14px; color: #8e96a1; font-size: 11px; }.completion-list { display: flex; flex-wrap: wrap; gap: 7px; }.completion-list span { display: flex; align-items: center; gap: 5px; padding: 5px 8px; border-radius: 999px; color: #a1a8b1; background: #f5f6f8; font-size: 10px; }.completion-list i { width: 5px; height: 5px; border-radius: 50%; background: #c9cdd3; }.completion-list span.complete { color: #4e9c8a; background: #eaf9f5; }.completion-list span.complete i { background: #68cdb5; }
.tip-card { display: flex; align-items: flex-start; gap: 12px; padding: 18px 20px; border-radius: 20px; background: linear-gradient(145deg,rgba(255,255,255,.92),rgba(241,237,255,.82)); }.tip-card > span { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; border-radius: 12px; color: #806dbd; background: #ece6ff; }.tip-card strong { color: #3a3e46; font-size: 12px; }.tip-card p { margin: 6px 0 0; color: #939aa5; font-size: 10px; line-height: 1.7; }
@keyframes hero-orb { 0%,100% { transform: translate(0,0); } 50% { transform: translate(16px,10px); } } @keyframes star-float { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-8px) rotate(16deg); } } @keyframes orbit-spin { to { transform: rotate(360deg); } }
@media (max-width: 1020px) { .edit-layout { grid-template-columns: 1fr; }.preview-column { position: static; grid-template-columns: 1.1fr .9fr; }.tip-card { grid-column: 1 / -1; } }
@media (max-width: 760px) { .profile-hero { grid-template-columns: 1fr; min-height: auto; }.hero-decoration { display: none; }.field-grid { grid-template-columns: 1fr; }.preview-column { grid-template-columns: 1fr; }.tip-card { grid-column: auto; }.form-actions { align-items: flex-start; flex-direction: column; }.form-actions > div:last-child { width: 100%; }.form-actions .el-button { flex: 1; } }
@media (max-width: 480px) { .profile-hero { padding: 26px 21px; border-radius: 24px; }.profile-hero h1 { font-size: 34px; letter-spacing: -1.4px; }.form-panel { padding: 20px 17px; border-radius: 22px; }.form-panel__heading { flex-direction: column; }.section-heading { align-items: flex-start; }.form-actions > div:last-child { flex-direction: column-reverse; }.form-actions .el-button { width: 100%; margin-left: 0; } }
@media (prefers-reduced-motion: reduce) { .profile-hero::before, .hero-star, .completion-orbit { animation: none; }.pixel-face, .profile-back-button { transition: none; }.profile-hero:hover .pixel-face, .profile-back-button:hover { transform: none; } }
</style>
