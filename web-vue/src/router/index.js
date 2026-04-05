import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Sessions from '@/views/Sessions.vue'
import SessionDetail from '@/views/SessionDetail.vue'
import RequestDetail from '@/views/RequestDetail.vue'
import Analysis from '@/views/Analysis.vue'
import Settings from '@/views/Settings.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { title: 'Dashboard' }
  },
  {
    path: '/sessions',
    name: 'Sessions',
    component: Sessions,
    meta: { title: 'Sessions' }
  },
  {
    path: '/sessions/:id',
    name: 'SessionDetail',
    component: SessionDetail,
    meta: { title: 'Session Detail' },
    props: true
  },
  {
    path: '/requests/:id',
    name: 'RequestDetail',
    component: RequestDetail,
    meta: { title: 'Request Detail' },
    props: true
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: Analysis,
    meta: { title: 'Analysis' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { title: 'Settings' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - Claude Code Capture` : 'Claude Code Capture'
  next()
})

export default router
