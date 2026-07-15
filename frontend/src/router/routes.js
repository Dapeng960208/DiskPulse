// @unocss-include to extract icon class
import AppLayout from '@/layouts/AppLayout.vue';
import { hasRole } from '@/utils/authorization';

export default [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/auth/LoginPage.vue'),
    meta: {
      title: '登录',
      isPublic: true,
    },
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/pages/dashboard/DashboardPage.vue'),
        meta: {
          title: '概览',
          isRoot: true,
          menuOrder: 10,
          icon: 'i-ri-dashboard-2-line',
        },
      },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: 'usage',
        name: 'Usages',
        component: () => import('@/pages/usage/UsageListPage.vue'),
        meta: {
          title: '用户',
          isRoot: true,
          menuOrder: 20,
          icon: 'i-ri-user-line',
        },
      },
      {
        path: 'usage/:id',
        name: 'UsagesDetail',
        component: () => import('@/pages/usage/UsageDetailPage.vue'),
        meta: {
          title: '使用详情',
          isHidden: true,
        },
      },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '/projects',
        name: 'Projects',
        component: () => import('@/pages/project/ProjectListPage.vue'),
        meta: {
          title: '项目',
          isRoot: true,
          menuOrder: 30,
          icon: 'i-ri-projector-2-line',
        },
      },
      {
        path: '/project/:id',
        name: 'ProjectDetail',
        component: () => import('@/pages/project/ProjectDetailPage.vue'),
        meta: {
          title: '项目组详情',
          isHidden: true,
        },
      },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: 'groups',
        name: 'Groups',
        component: () => import('@/pages/group/GroupListPage.vue'),
        meta: {
          title: '项目组',
          isRoot: true,
          menuOrder: 40,
          icon: 'i-ri-group-2-line',
        },
      },
      {
        path: 'group/:id',
        name: 'GroupDetail',
        component: () => import('@/pages/group/GroupDetailPage.vue'),
        meta: {
          title: '项目组详情',
          isHidden: true,
        },
      },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/pages/alert/AlertListPage.vue'),
        meta: {
          title: '告警',
          isRoot: true,
          menuOrder: 60,
          icon: 'i-ri-alarm-warning-line',
        },
      },
      {
        path: 'ai/chat',
        name: 'AIChat',
        component: () => import('@/pages/ai/AiChatPage.vue'),
        meta: {
          title: 'AI 助手',
          isRoot: true,
          menuOrder: 50,
          icon: 'i-ri-sparkling-2-line',
        },
      },
    ],
  },
  {
    path: '/admin',
    component: AppLayout,
    meta: {
      title: '系统管理',
      icon: 'i-ri-settings-line',
      isRoot: true,
      menuOrder: 70,
      // isAccessible: () => hasRole('diskpulse:admin') ? 200 : 403,
    },
    children: [
      {
        path: 'group-tags',
        name: 'GroupTags',
        component: () => import('@/pages/group-tag/GroupTagListPage.vue'),
        meta: {
          title: '项目组标签',
        },
      },
      {
        path: 'storage-clusters',
        name: 'StorageClusters',
        component: () => import('@/pages/admin/storage-cluster/StorageClusterListPage.vue'),
        meta: {
          title: '存储集群',
        },
      },
      {
        path: 'storage-cluster/:id',
        name: 'StorageClusterDetail',
        component: () => import('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue'),
        meta: {
          title: '存储集群详情',
          isHidden: true,
        },
      },
      {
        path: 'aggregates',
        name: 'Aggregates',
        component: () => import('@/pages/admin/aggregate/AggregateListPage.vue'),
        meta: {
          title: '容量池',
        },
      },
      {
        path: 'aggregate/:id',
        name: 'AggregateDetail',
        component: () => import('@/pages/admin/aggregate/AggregateDetailPage.vue'),
        meta: {
          title: '容量池详情',
          isHidden: true,
        },
      },
      {
        path: 'volumes',
        name: 'Volumes',
        component: () => import('@/pages/admin/volume/VolumeListPage.vue'),
        meta: {
          title: '存储空间',
        },
      },
      {
        path: 'volume/:id',
        name: 'VolumeDetail',
        component: () => import('@/pages/admin/volume/VolumeDetailPage.vue'),
        meta: {
          title: '存储空间详情',
          isHidden: true,
        },
      },
      {
        path: 'qtrees',
        name: 'Qtrees',
        component: () => import('@/pages/admin/qtree/QtreeListPage.vue'),
        meta: {
          title: 'Qtree（NetApp）',
        },
      },
      {
        path: 'qtree/:id',
        name: 'QtreeDetail',
        component: () => import('@/pages/admin/qtree/QtreeDetailPage.vue'),
        meta: {
          title: 'Qtree（NetApp）详情',
          isHidden: true,
        },
      },
      {
        path: 'users',
        name: 'UsersManagement',
        component: () => import('@/pages/admin/user/UserListPage.vue'),
        meta: {
          title: '用户信息管理',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'backup',
        name: 'BackUp',
        component: () => import('@/pages/admin/backup/BackUpListPage.vue'),
        meta: {
          title: '离职备份',
          isHidden: true,
        },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/pages/admin/settings/SettingsPage.vue'),
        meta: {
          title: '系统设置',
        },
      },
      {
        path: 'ai-center',
        name: 'AICenter',
        component: () => import('@/pages/admin/ai/AiCenterPage.vue'),
        meta: {
          title: 'AI 中心',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'ai-center/audits/:id',
        name: 'AIAuditDetail',
        component: () => import('@/pages/admin/ai/AiAuditDetailPage.vue'),
        meta: {
          title: 'AI 审计详情',
          isHidden: true,
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
    ],
  },

  {
    path: '/403',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'Unauthorized',
        component: () => import('@/pages/error/UnauthorizedPage.vue'),
      },
    ],
  },
  {
    path: '/404',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'NotFound',
        component: () => import('@/pages/error/NotFoundPage.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'Unknown',
    redirect: '/404',
  },
];
