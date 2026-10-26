import { createApp } from 'vue'
import { createPinia } from 'pinia'

import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import { installEmailRequestPolicy } from '@/features/email-verification/policy'

const app = createApp(App)

app.use(createPinia())
// 独立邮箱前置检查在路由初始化前注册，不重写原认证拦截器。
installEmailRequestPolicy()
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 全局注册 Element Plus 图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
