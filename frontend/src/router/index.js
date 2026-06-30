import { createRouter, createWebHistory } from 'vue-router';
import nProgress from 'nprogress';
import routes from './routes';
import { useCurrentUser } from '@/stores/current-user';
import { updatePageSubtitle } from '@/utils';
import { hasAnyRole } from '@/utils/authorization';
import usersApi from '@/api/users-api';
import { processRoutes, shouldUpdatePageSubtitle } from '@/router/support/accessibility';
import 'nprogress/nprogress.css';

nProgress.configure({
  showSpinner: false,
});

processRoutes(routes);

const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_APP_BASE),
  routes,
  scrollBehavior: (to, from, savedPosition) => {
    if (savedPosition) {
      return savedPosition;
    }

    return { top: 0 };
  },
});

const whiteList = ['/404', '/login'];
const requiredRoles = [];

router.beforeEach(async (to, from) => {
  nProgress.start();

  if (to.meta.isPublic || whiteList.includes(to.path)) {
    shouldUpdatePageSubtitle(to, from, updatePageSubtitle);
    return;
  }

  const currentUser = useCurrentUser();

  try {
    const { result } = await usersApi.fetchProfile();

    currentUser.setCurrentUser(result);

    if (requiredRoles.length > 0 && !hasAnyRole(requiredRoles)) {
      return '/403';
    }

    if (!to.meta.isAccessible) {
      shouldUpdatePageSubtitle(to, from, updatePageSubtitle);
      return;
    }

    switch (to.meta.isAccessible()) {
      case 200:
        shouldUpdatePageSubtitle(to, from, updatePageSubtitle);
        return;
      case 403:
        return '/403';
      case 404:
        return '/404';
      default:
        return '/404';
    }
  } catch (error) {
    console.error(error);
  }
});

router.afterEach(() => {
  nProgress.done();
});

export default router;
