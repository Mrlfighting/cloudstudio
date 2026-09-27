<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const beads = [
  'empty', 'rose', 'rose', 'empty', 'empty', 'empty', 'rose', 'rose', 'empty',
  'rose', 'pink', 'pink', 'rose', 'empty', 'rose', 'pink', 'pink', 'rose',
  'rose', 'pink', 'cream', 'pink', 'rose', 'pink', 'cream', 'pink', 'rose',
  'empty', 'rose', 'pink', 'pink', 'pink', 'pink', 'pink', 'rose', 'empty',
  'empty', 'empty', 'rose', 'pink', 'pink', 'pink', 'rose', 'empty', 'empty',
  'empty', 'empty', 'empty', 'rose', 'pink', 'rose', 'empty', 'empty', 'empty',
  'empty', 'empty', 'empty', 'empty', 'rose', 'empty', 'empty', 'empty', 'empty',
]
</script>

<template>
  <main class="beads-page">
    <span class="beads-orb beads-orb--blue" aria-hidden="true"></span>
    <span class="beads-orb beads-orb--pink" aria-hidden="true"></span>
    <section class="beads-card">
      <div class="beads-visual" aria-hidden="true">
        <div class="beads-board">
          <span
            v-for="(bead, index) in beads"
            :key="index"
            class="bead"
            :class="`bead--${bead}`"
            :style="{ '--bead-delay': `${index * 18}ms` }"
          ></span>
        </div>
        <span class="beads-badge">COMING SOON</span>
      </div>

      <div class="beads-copy">
        <div class="beads-kicker">PIXEL BEADS · 创意实验室</div>
        <h1>拼豆工坊</h1>
        <p>功能正在开发中，敬请期待。</p>
        <p class="beads-description">未来你可以在这里把喜爱的图片转换为拼豆创作灵感。</p>
        <el-button type="primary" size="large" @click="router.push('/pictures')">
          <el-icon><Compass /></el-icon>
          返回探索
        </el-button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.beads-page {
  position: relative;
  width: min(1280px, 100%);
  min-height: calc(100vh - 72px);
  margin: 0 auto;
  padding: clamp(36px, 7vw, 92px) var(--app-page-x);
  display: grid;
  place-items: center;
  overflow: hidden;
}

.beads-page::before {
  content: '';
  position: absolute;
  inset: 7% 4%;
  border-radius: 44px;
  background:
    linear-gradient(rgba(255,255,255,.48), rgba(255,255,255,.48)),
    radial-gradient(circle at 20% 20%, rgba(159,220,244,.42), transparent 34%),
    radial-gradient(circle at 82% 74%, rgba(236,114,150,.35), transparent 32%);
}

.beads-card {
  position: relative;
  z-index: 1;
  width: min(940px, 100%);
  display: grid;
  grid-template-columns: minmax(280px, .85fr) minmax(340px, 1.15fr);
  align-items: center;
  gap: clamp(36px, 7vw, 88px);
  padding: clamp(34px, 6vw, 72px);
  border: 1px solid rgba(255,255,255,.82);
  border-radius: 36px;
  background: rgba(255,255,255,.76);
  box-shadow: 0 38px 90px rgba(38,42,52,.13);
  backdrop-filter: blur(22px);
}

.beads-visual { position: relative; display: grid; place-items: center; }
.beads-board {
  width: min(310px, 76vw);
  aspect-ratio: 1;
  display: grid;
  grid-template-columns: repeat(9, 1fr);
  gap: 7px;
  padding: 20px;
  border-radius: 31px;
  background: linear-gradient(145deg, #fff, #f4f6fa);
  box-shadow: 18px 24px 45px rgba(45,50,65,.14), inset 0 0 0 1px #e8eaf0;
  transform: rotate(-4deg);
  animation: board-float 4.2s ease-in-out infinite;
}

.bead {
  aspect-ratio: 1;
  border-radius: 50%;
  opacity: 0;
  transform: scale(.2);
  animation: bead-pop .46s cubic-bezier(.34, 1.56, .64, 1) forwards;
  animation-delay: var(--bead-delay);
  box-shadow: inset -3px -4px 6px rgba(36,41,48,.12), inset 3px 3px 5px rgba(255,255,255,.72);
}
.bead--empty { visibility: hidden; }
.bead--rose { background: #eb6f95; }
.bead--pink { background: #f4a1b9; }
.bead--cream { background: #fff0cc; }
.beads-badge {
  position: absolute;
  right: -18px;
  bottom: -18px;
  padding: 10px 16px;
  border-radius: 999px;
  color: #7668b0;
  background: #eeeaff;
  box-shadow: 0 12px 28px rgba(105,90,170,.18);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.beads-copy { animation: copy-enter .72s .18s cubic-bezier(.22, 1, .36, 1) both; }
.beads-kicker { margin-bottom: 14px; color: #b16880; font-size: 11px; font-weight: 900; letter-spacing: 2px; }
.beads-copy h1 { margin: 0; color: #1e2229; font-size: clamp(44px, 6vw, 72px); line-height: 1; font-weight: 950; letter-spacing: -3px; }
.beads-copy > p { margin: 20px 0 0; color: #4f5864; font-size: 20px; font-weight: 700; }
.beads-copy .beads-description { max-width: 480px; margin-top: 10px; color: #929ba7; font-size: 14px; font-weight: 500; line-height: 1.8; }
.beads-copy .el-button { margin-top: 30px; min-width: 150px; height: 48px; }
.beads-orb { position: absolute; z-index: 0; border-radius: 50%; filter: blur(2px); animation: orb-drift 7s ease-in-out infinite alternate; }
.beads-orb--blue { width: 160px; height: 160px; left: 1%; top: 11%; background: rgba(159,220,244,.38); }
.beads-orb--pink { width: 220px; height: 220px; right: -3%; bottom: 6%; background: rgba(249,175,197,.3); animation-delay: -2s; }

@keyframes bead-pop { to { opacity: 1; transform: scale(1); } }
@keyframes board-float { 0%,100% { transform: rotate(-4deg) translateY(0); } 50% { transform: rotate(-2deg) translateY(-12px); } }
@keyframes orb-drift { to { transform: translate(24px, -18px) scale(1.08); } }
@keyframes copy-enter { from { opacity: 0; transform: translateX(26px); } to { opacity: 1; transform: translateX(0); } }

@media (max-width: 760px) {
  .beads-page { min-height: calc(100vh - 62px); }
  .beads-card { grid-template-columns: 1fr; text-align: center; gap: 44px; }
  .beads-board { width: min(280px, 70vw); gap: 6px; padding: 16px; }
  .beads-badge { right: -8px; }
  .beads-copy .beads-description { margin-left: auto; margin-right: auto; }
}

@media (prefers-reduced-motion: reduce) {
  .beads-board, .beads-orb, .beads-copy, .bead { animation: none; }
  .bead { opacity: 1; transform: scale(1); }
}
</style>
