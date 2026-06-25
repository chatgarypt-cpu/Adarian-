import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './style.css';

const savedRoute = window.localStorage.getItem('adarian:last-route');
const workflowPaths = new Set(['/seed', '/config', '/models', '/run', '/review', '/report', '/history', '/settings']);
if (savedRoute && workflowPaths.has(savedRoute) && savedRoute !== window.location.pathname) {
  window.history.replaceState(null, '', savedRoute);
} else if (savedRoute && !workflowPaths.has(savedRoute)) {
  window.localStorage.removeItem('adarian:last-route');
}

createApp(App).use(createPinia()).use(router).mount('#app');
