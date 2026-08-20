/**
 * 路由表与守卫
 * - requiresAuth：需登录
 * - requiresAdmin：需管理员
 * - guestOnly：已登录用户访问登录/注册页时跳转个人中心
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: '登录', guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { title: '注册', guestOnly: true },
    },
    {
      path: '/',
      component: DefaultLayout,
      children: [
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue'),
          meta: { title: '个人中心', requiresAuth: true },
        },
        {
          path: 'profile/edit',
          name: 'edit-profile',
          component: () => import('@/views/EditProfileView.vue'),
          meta: { title: '编辑资料', requiresAuth: true },
        },
        {
          path: 'pictures',
          name: 'picture-list',
          component: () => import('@/views/pictures/PictureListView.vue'),
          meta: { title: '图片库', requiresAuth: true },
        },
        {
          path: 'pictures/my',
          name: 'my-uploads',
          component: () => import('@/views/pictures/MyUploadsView.vue'),
          meta: { title: '我的上传', requiresAuth: true },
        },
        {
          path: 'pictures/manage',
          name: 'picture-manage',
          component: () => import('@/views/pictures/admin/PictureManageView.vue'),
          meta: { title: '图片管理', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'pictures/:id',
          name: 'picture-detail',
          component: () => import('@/views/pictures/PictureDetailView.vue'),
          meta: { title: '图片详情', requiresAuth: true },
        },
        {
          path: 'admin/users',
          name: 'user-manage',
          component: () => import('@/views/admin/UserManageView.vue'),
          meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'spaces',
          name: 'space-home',
          component: () => import('@/views/space/SpaceHomeView.vue'),
          meta: { title: '我的空间', requiresAuth: true },
        },
        {
          path: 'spaces/create',
          name: 'space-create',
          component: () => import('@/views/space/SpaceCreateView.vue'),
          meta: { title: '创建空间', requiresAuth: true },
        },
        {
          path: 'spaces/gallery',
          name: 'space-gallery',
          component: () => import('@/views/space/SpaceGalleryView.vue'),
          meta: { title: '空间图册', requiresAuth: true },
        },
        {
          path: 'spaces/pictures/:id',
          name: 'space-picture-detail',
          component: () => import('@/views/space/SpacePictureDetailView.vue'),
          meta: { title: '空间图片详情', requiresAuth: true },
        },
        {
          path: 'spaces/manage',
          name: 'space-manage',
          component: () => import('@/views/space/admin/SpaceManageView.vue'),
          meta: { title: '空间管理', requiresAuth: true, requiresAdmin: true },
        },
        { path: '', redirect: '/profile' },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/profile' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.initialize()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { path: '/profile' }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { path: '/profile' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 用户中心` : '用户中心'
})

export default router
