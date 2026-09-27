<script setup lang="ts">
import SiteFooter from '@/components/SiteFooter.vue'

withDefaults(defineProps<{
  mode: 'login' | 'register'
  eyebrow: string
  title: string
  subtitle: string
}>(), {})
</script>

<template>
  <div class="auth-page" :class="`auth-page--${mode}`">
    <div class="auth-atmosphere" aria-hidden="true">
      <span class="glow glow--sky"></span>
      <span class="glow glow--rose"></span>
      <span class="glow glow--lavender"></span>
      <span class="orbit orbit--one"></span>
      <span class="orbit orbit--two"></span>
      <div class="floating-pixels"><i v-for="index in 12" :key="index"></i></div>
    </div>

    <main class="auth-shell analytics-reveal">
      <section class="auth-story">
        <router-link class="brand" to="/pictures" aria-label="返回云上工坊探索页">
          <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
          <span><strong>云上工坊</strong><small>CLOUD ATELIER</small></span>
        </router-link>

        <div class="story-copy">
          <div class="story-eyebrow">{{ mode === 'login' ? 'WELCOME BACK' : 'CREATE TOGETHER' }}</div>
          <h1 v-if="mode === 'login'">让每一次回来<br />都有新的<span>灵感</span></h1>
          <h1 v-else>从今天开始<br />收藏你的<span>灵感宇宙</span></h1>
          <p v-if="mode === 'login'">继续浏览精选图库，管理个人素材，并与团队分享每一次创作发现。</p>
          <p v-else>建立专属创作身份，把喜欢的素材、颜色和项目灵感沉淀在同一个地方。</p>
        </div>

        <div class="story-features">
          <div><span class="feature-icon feature-icon--rose"><el-icon><PictureFilled /></el-icon></span><span><strong>探索图库</strong><small>发现精选视觉素材</small></span></div>
          <div><span class="feature-icon feature-icon--sky"><el-icon><FolderOpened /></el-icon></span><span><strong>个人空间</strong><small>整理自己的创作资产</small></span></div>
          <div><span class="feature-icon feature-icon--mint"><el-icon><UserFilled /></el-icon></span><span><strong>团队协作</strong><small>与成员共享灵感进度</small></span></div>
        </div>

        <div class="story-art" aria-hidden="true">
          <div class="art-card art-card--back"><span></span><span></span><span></span></div>
          <div class="art-card art-card--front">
            <div class="bead-heart">
              <i v-for="index in 25" :key="index" :class="{ filled: [3, 5, 7, 8, 9, 11, 12, 13, 14, 15, 17, 18, 19, 23].includes(index) }"></i>
            </div>
            <div class="art-lines"><span></span><span></span></div>
          </div>
        </div>
      </section>

      <section class="auth-form-zone">
        <div class="form-card">
          <div class="form-card__head">
            <span class="form-symbol" :class="`form-symbol--${mode}`">
              <el-icon><component :is="mode === 'login' ? 'Key' : 'Plus'" /></el-icon>
            </span>
            <div class="form-eyebrow">{{ eyebrow }}</div>
            <h2>{{ title }}<span>.</span></h2>
            <p>{{ subtitle }}</p>
          </div>

          <div class="form-card__body"><slot /></div>

          <div class="trust-note">
            <el-icon><Lock /></el-icon>
            <span>会话信息将被安全保存，仅用于维持登录状态</span>
          </div>
        </div>

        <router-link class="back-explore" to="/pictures">
          <el-icon><ArrowLeft /></el-icon>
          暂不登录，返回探索
        </router-link>
      </section>
    </main>

    <SiteFooter fixed />
  </div>
</template>

<style scoped>
.auth-page {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 48px clamp(22px, 5vw, 78px) 74px;
  overflow: hidden auto;
  background:
    radial-gradient(circle at 9% 8%, rgba(146, 217, 242, .42), transparent 27%),
    radial-gradient(circle at 91% 5%, rgba(244, 157, 185, .36), transparent 26%),
    radial-gradient(circle at 83% 91%, rgba(191, 234, 223, .34), transparent 25%),
    linear-gradient(126deg, #edf9fc 0%, #fff9fb 50%, #f7f4ff 100%);
}

.auth-page::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: .26;
  background-image:
    linear-gradient(rgba(255,255,255,.78) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.78) 1px, transparent 1px);
  background-size: 38px 38px;
  mask-image: linear-gradient(to bottom, #000, transparent 84%);
}

.auth-atmosphere { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }
.glow { position: absolute; border-radius: 50%; filter: blur(2px); animation: glow-drift 9s ease-in-out infinite; }
.glow--sky { width: 250px; height: 250px; left: -80px; top: 12%; background: rgba(126,207,236,.22); }
.glow--rose { width: 210px; height: 210px; right: -58px; top: 18%; background: rgba(236,114,150,.2); animation-delay: -3s; }
.glow--lavender { width: 190px; height: 190px; left: 42%; bottom: -95px; background: rgba(155,137,223,.18); animation-delay: -6s; }
.orbit { position: absolute; border: 1px solid rgba(255,255,255,.72); border-radius: 50%; }
.orbit--one { width: 480px; height: 480px; left: -215px; top: -215px; }
.orbit--two { width: 390px; height: 390px; right: -180px; bottom: -195px; }
.floating-pixels i { position: absolute; width: 10px; height: 10px; border-radius: 3px; background: rgba(236,114,150,.42); animation: pixel-float 5s ease-in-out infinite; }
.floating-pixels i:nth-child(1) { left: 6%; top: 30%; }.floating-pixels i:nth-child(2) { left: 12%; bottom: 18%; background: rgba(98,196,233,.5); animation-delay: -1s; }.floating-pixels i:nth-child(3) { left: 44%; top: 8%; background: rgba(104,205,181,.48); animation-delay: -2.2s; }.floating-pixels i:nth-child(4) { right: 8%; top: 37%; width: 7px; height: 7px; }.floating-pixels i:nth-child(5) { right: 17%; bottom: 13%; background: rgba(155,137,223,.44); animation-delay: -1.8s; }.floating-pixels i:nth-child(6) { left: 51%; bottom: 9%; width: 6px; height: 6px; background: rgba(98,196,233,.5); }.floating-pixels i:nth-child(n+7) { display: none; }

.auth-shell {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(390px, .92fr);
  width: min(1160px, 100%);
  min-height: 650px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.92);
  border-radius: 34px;
  background: rgba(255,255,255,.54);
  box-shadow: 0 36px 100px rgba(58,66,86,.16);
  backdrop-filter: blur(24px);
}

.auth-story { position: relative; display: flex; flex-direction: column; min-width: 0; padding: clamp(36px, 5vw, 62px); overflow: hidden; background: linear-gradient(145deg, rgba(233,248,253,.86), rgba(255,241,246,.72) 55%, rgba(238,234,255,.76)); }
.auth-story::after { content: ''; position: absolute; width: 260px; height: 260px; right: -100px; top: -100px; border-radius: 50%; background: rgba(255,255,255,.37); }
.brand { position: relative; z-index: 2; display: inline-flex; align-items: center; gap: 12px; width: max-content; color: #242930; text-decoration: none; }
.brand-mark { display: grid; grid-template-columns: repeat(2, 12px); gap: 3px; padding: 7px; border-radius: 11px; background: rgba(255,255,255,.74); box-shadow: 0 9px 20px rgba(82,91,113,.11); transform: rotate(-4deg); transition: transform .3s ease; }
.brand:hover .brand-mark { transform: rotate(0) scale(1.05); }.brand-mark i { width: 12px; height: 12px; border-radius: 4px; background: #ec7296; }.brand-mark i:nth-child(2) { background: #81cce9; }.brand-mark i:nth-child(3) { background: #73cbb7; }.brand-mark i:nth-child(4) { background: #a493df; }
.brand strong, .brand small { display: block; }.brand strong { font-size: 16px; font-weight: 900; }.brand small { margin-top: 2px; color: #9895a0; font-size: 8px; font-weight: 800; letter-spacing: 1.5px; }
.story-copy { position: relative; z-index: 2; margin-top: clamp(54px, 8vh, 92px); }.story-eyebrow { color: #a16b7d; font-size: 10px; font-weight: 900; letter-spacing: 2.6px; }.story-copy h1 { margin: 13px 0 0; color: #1c2027; font-size: clamp(37px, 4.2vw, 58px); line-height: 1.12; letter-spacing: -2px; font-weight: 900; }.story-copy h1 span { margin-left: 5px; color: transparent; background: linear-gradient(90deg,#d56788,#778fda); background-clip: text; -webkit-background-clip: text; }.story-copy p { max-width: 530px; margin: 20px 0 0; color: #78818e; font-size: 14px; line-height: 1.9; }
.story-features { position: relative; z-index: 2; display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px; margin-top: 32px; }.story-features > div { display: flex; align-items: center; gap: 9px; min-width: 0; padding: 11px; border: 1px solid rgba(255,255,255,.7); border-radius: 15px; background: rgba(255,255,255,.44); }.feature-icon { display: grid; place-items: center; flex: 0 0 auto; width: 31px; height: 31px; border-radius: 10px; }.feature-icon--rose { color: #cd6382; background: #fff0f5; }.feature-icon--sky { color: #4fa8cc; background: #eaf9ff; }.feature-icon--mint { color: #48a48e; background: #e8faf5; }.story-features strong, .story-features small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.story-features strong { color: #4a4f58; font-size: 10px; }.story-features small { margin-top: 3px; color: #9ba2ad; font-size: 8px; }
.story-art { position: relative; z-index: 2; height: 112px; margin-top: auto; }.art-card { position: absolute; border: 1px solid rgba(255,255,255,.86); border-radius: 18px; background: rgba(255,255,255,.67); box-shadow: 0 16px 35px rgba(73,81,101,.11); backdrop-filter: blur(12px); }.art-card--back { left: 8%; bottom: -43px; width: 190px; height: 116px; padding: 20px; transform: rotate(-7deg); }.art-card--back span { display: block; height: 7px; margin-bottom: 10px; border-radius: 7px; background: #e9eaf0; }.art-card--back span:nth-child(1) { width: 65%; background: #f3b2c5; }.art-card--back span:nth-child(2) { width: 88%; }.art-card--back span:nth-child(3) { width: 48%; }.art-card--front { right: 8%; bottom: -32px; display: flex; align-items: center; gap: 18px; width: 220px; height: 135px; padding: 20px; transform: rotate(6deg); transition: transform .4s cubic-bezier(.22,1,.36,1); }.auth-story:hover .art-card--front { transform: rotate(2deg) translateY(-7px); }.bead-heart { display: grid; grid-template-columns: repeat(5, 9px); gap: 3px; }.bead-heart i { width: 9px; height: 9px; border-radius: 3px; background: #edf0f4; }.bead-heart i.filled { background: linear-gradient(135deg,#f291ae,#de6589); box-shadow: inset 0 -2px 3px rgba(159,62,92,.13); }.art-lines { flex: 1; }.art-lines span { display: block; height: 7px; margin-bottom: 10px; border-radius: 6px; background: #e9ebf0; }.art-lines span:first-child { width: 74%; background: #a9def1; }

.auth-form-zone { display: flex; flex-direction: column; justify-content: center; padding: clamp(34px, 5vw, 66px); background: rgba(255,255,255,.8); }.form-card { width: min(420px, 100%); margin: auto; }.form-card__head { margin-bottom: 27px; }.form-symbol { display: grid; place-items: center; width: 45px; height: 45px; margin-bottom: 20px; border-radius: 15px; color: #cb5f80; background: #fff0f5; box-shadow: 9px 9px 0 rgba(236,114,150,.1); }.form-symbol--register { color: #647bc0; background: #eeefff; box-shadow: 9px 9px 0 rgba(127,146,214,.1); }.form-eyebrow { color: #ab7385; font-size: 9px; font-weight: 900; letter-spacing: 2.2px; }.form-card__head h2 { margin: 8px 0 0; color: #1f232a; font-size: 34px; letter-spacing: -1px; }.form-card__head h2 span { color: #ec7296; }.form-card__head p { margin: 8px 0 0; color: #959ca7; font-size: 12px; line-height: 1.7; }
.form-card__body :deep(.el-form-item) { margin-bottom: 19px; }.form-card__body :deep(.el-form-item__label) { padding-bottom: 8px; color: #626a75; font-size: 12px; }.form-card__body :deep(.el-input__wrapper) { min-height: 47px; padding: 1px 14px; border-radius: 13px !important; background: #f8f9fb; box-shadow: 0 0 0 1px #e8eaf0 inset !important; transition: background .2s ease, box-shadow .2s ease, transform .2s ease; }.form-card__body :deep(.el-input__wrapper:hover) { background: #fff; box-shadow: 0 0 0 1px #edb2c3 inset !important; }.form-card__body :deep(.el-input__wrapper.is-focus) { background: #fff; box-shadow: 0 0 0 1px #ec83a2 inset, 0 8px 22px rgba(236,114,150,.1) !important; transform: translateY(-1px); }.form-card__body :deep(.el-textarea__inner) { min-height: 74px !important; padding: 13px 14px; border-radius: 13px !important; background: #f8f9fb; line-height: 1.7; }.form-card__body :deep(.auth-submit) { height: 48px; margin-top: 3px; border-radius: 13px; background: linear-gradient(105deg,#e86f93,#dd668b 52%,#a783d4); border: 0; box-shadow: 0 13px 28px rgba(221,102,139,.27); transition: transform .22s ease, box-shadow .22s ease; }.form-card__body :deep(.auth-submit:hover) { transform: translateY(-2px); box-shadow: 0 17px 34px rgba(221,102,139,.34); }.form-card__body :deep(.auth-switch) { margin-top: 5px; }
.trust-note { display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 19px; color: #a4abb4; font-size: 9px; }.back-explore { display: inline-flex; align-items: center; align-self: center; gap: 6px; margin-top: 25px; color: #8d95a0; font-size: 11px; font-weight: 700; text-decoration: none; transition: color .2s ease, transform .2s ease; }.back-explore:hover { color: #bd5c7a; transform: translateX(-3px); }

@keyframes glow-drift { 0%,100% { transform: translate3d(0,0,0); } 50% { transform: translate3d(14px,-12px,0); } }
@keyframes pixel-float { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-9px) rotate(12deg); } }

@media (max-width: 940px) {
  .auth-page { padding: 28px 24px 76px; }
  .auth-shell { grid-template-columns: 1fr; width: min(580px,100%); }
  .auth-story { min-height: 280px; padding: 32px 38px; }
  .story-copy { margin-top: 35px; }.story-copy h1 { font-size: 38px; }.story-copy p { margin-top: 12px; }
  .story-features, .story-art { display: none; }
  .auth-form-zone { padding: 38px; }
}

@media (max-width: 540px) {
  .auth-page { align-items: start; padding: 14px 12px 68px; }
  .auth-shell { border-radius: 25px; }
  .auth-story { min-height: 236px; padding: 27px 24px; }.story-copy { margin-top: 30px; }.story-copy h1 { font-size: 32px; letter-spacing: -1.2px; }.story-copy p { font-size: 12px; line-height: 1.7; }
  .auth-form-zone { padding: 30px 22px 32px; }.form-card__head h2 { font-size: 30px; }.form-card__head { margin-bottom: 23px; }
}

@media (prefers-reduced-motion: reduce) {
  .glow, .floating-pixels i { animation: none; }
  .brand-mark, .art-card--front, .form-card__body :deep(.auth-submit), .back-explore { transition: none; }
  .brand:hover .brand-mark, .auth-story:hover .art-card--front, .form-card__body :deep(.auth-submit:hover), .back-explore:hover { transform: none; }
}
</style>
