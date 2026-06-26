import { createRouter, createWebHistory } from 'vue-router';
import SeedPage from './pages/01-seed.vue';
import ConfigPage from './pages/02-config.vue';
import ModelsPage from './pages/03-models.vue';
import RunPage from './pages/04-run.vue';
import ReviewPage from './pages/05-review.vue';
import ReportPage from './pages/06-report.vue';
import HistoryPage from './pages/07-history.vue';
import SettingsPage from './pages/08-settings.vue';
import WorldPage from './pages/09-world.vue';

export const routes = [
  { path: '/', redirect: '/seed' },
  { path: '/seed', component: SeedPage },
  { path: '/config', component: ConfigPage },
  { path: '/models', component: ModelsPage },
  { path: '/run', component: RunPage },
  { path: '/review', component: ReviewPage },
  { path: '/report', component: ReportPage },
  { path: '/history', component: HistoryPage },
  { path: '/settings', component: SettingsPage },
  { path: '/world', component: WorldPage },
  { path: '/:pathMatch(.*)*', redirect: '/seed' },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  const workflowPaths = new Set(['/seed', '/config', '/models', '/run', '/review', '/report', '/history', '/settings', '/world']);
  if (typeof window !== 'undefined' && workflowPaths.has(to.path)) {
    window.localStorage.setItem('adarian:last-route', to.path);
  }
});
