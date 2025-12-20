import { createRouter, createWebHashHistory } from 'vue-router';

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/home', component: () => import('../views/Home.vue') },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;