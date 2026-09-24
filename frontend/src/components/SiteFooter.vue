<script setup lang="ts">
/**
 * 站点页脚：展示 ICP 备案号并链接至工信部官网
 *
 * @prop fixed 固定于视口底部（用于登录/注册等垂直居中的独立外壳页，
 *             避免页脚作为 flex 子项挤压居中卡片）
 */
const props = defineProps<{
  fixed?: boolean
}>()

const ICP_NUMBER = '赣ICP备2026023597号-1'
const MIIT_URL = 'https://beian.miit.gov.cn/'
</script>

<template>
  <footer class="site-footer" :class="{ 'is-fixed': props.fixed }">
    <a class="icp-link" :href="MIIT_URL" target="_blank" rel="noopener noreferrer">
      {{ ICP_NUMBER }}
    </a>
  </footer>
</template>

<style scoped>
.site-footer {
  margin-top: 46px;
  padding: 22px 0 10px;
  border-top: 1px solid var(--app-line-soft);
  text-align: center;
}

.icp-link {
  color: var(--app-muted);
  font-size: 13px;
  letter-spacing: 0.3px;
  text-decoration: none;
  transition: color 0.2s ease;
}

.icp-link:hover {
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
</style>
