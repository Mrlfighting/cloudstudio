<script setup lang="ts">
/**
 * 站点页脚：统一展示 ICP 备案与公安联网备案信息
 *
 * @prop fixed 固定于视口底部（用于登录/注册等垂直居中的独立外壳页，
 *             避免页脚作为 flex 子项挤压居中卡片）
 */
const props = defineProps<{
  fixed?: boolean
}>()

const ICP_NUMBER = '赣ICP备2026023597号-1'
const MIIT_URL = 'https://beian.miit.gov.cn/'
const PUBLIC_SECURITY_NUMBER = '赣公网安备36011102001339号'
const PUBLIC_SECURITY_URL = 'https://beian.mps.gov.cn/#/query/webSearch?code=36011102001339'
</script>

<template>
  <footer class="site-footer" :class="{ 'is-fixed': props.fixed }">
    <a class="icp-link" :href="MIIT_URL" target="_blank" rel="noopener noreferrer">
      {{ ICP_NUMBER }}
    </a>
    <a class="icp-link" :href="PUBLIC_SECURITY_URL" target="_blank" rel="noopener noreferrer">
      <img class="filing-icon" src="/备案图标.png" alt="" width="18" height="18" />
      {{ PUBLIC_SECURITY_NUMBER }}
    </a>
  </footer>
</template>

<style scoped>
.site-footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 8px 20px;
  margin-top: 46px;
  padding: 22px 0 10px;
  border-top: 1px solid var(--app-line-soft);
  text-align: center;
}

.icp-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  color: var(--app-muted);
  font-size: 13px;
  letter-spacing: 0.3px;
  text-decoration: none;
  transition: color 0.2s ease;
}

.filing-icon {
  flex-shrink: 0;
  object-fit: contain;
}

.icp-link:hover,
.icp-link:focus-visible {
  color: var(--app-primary);
}

/* 固定贴底模式：不占文档流、不遮挡页面元素点击 */
.site-footer.is-fixed {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  margin-top: 0;
  padding: 12px 0 16px;
  border-top: none;
  pointer-events: none;
}

.site-footer.is-fixed .icp-link {
  pointer-events: auto;
}

@media (max-width: 560px) {
  /* 小屏将整条备案链接换行，图标与备案号始终保持同一行。 */
  .site-footer { gap: 6px 14px; margin-top: 32px; padding: 18px 12px calc(10px + env(safe-area-inset-bottom)); }
  .site-footer.is-fixed { padding-bottom: calc(12px + env(safe-area-inset-bottom)); }
  .icp-link { font-size: 11px; }
}
</style>
