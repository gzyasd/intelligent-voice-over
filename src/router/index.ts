import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('@/pages/ProjectLibrary.vue'),
  },
  {
    path: '/current',
    name: 'current',
    component: () => import('@/pages/ProjectOverview.vue'),
  },
  {
    path: '/model-services',
    name: 'model-services',
    component: () => import('@/pages/ModelCenter.vue'),
  },
  {
    path: '/schemes',
    name: 'schemes',
    component: () => import('@/pages/Schemes.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/pages/Settings.vue'),
  },
  {
    path: '/pipeline',
    name: 'pipeline',
    component: () => import('@/pages/PipelineRun.vue'),
    meta: { requiresProject: true },
  },
  {
    path: '/timeline',
    name: 'timeline',
    component: () => import('@/pages/TimelineEditor.vue'),
    meta: { requiresProject: true },
  },
  {
    path: '/export',
    name: 'export',
    component: () => import('@/pages/Export.vue'),
    meta: { requiresProject: true },
  },
  // catch-all：未匹配的路由重定向到首页
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：需要项目路径的页面在缺少 query.path 时重定向到项目库
router.beforeEach((to) => {
  if (to.meta.requiresProject && !to.query.path) {
    return { name: 'projects' }
  }
  return true
})

export default router
