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
          title: '用户目录',
          isHidden: true,
          icon: 'i-ri-folder-user-line',
        },
      },
      {
        path: 'usage/:id',
        name: 'UsagesDetail',
        component: () => import('@/pages/usage/UsageDetailPage.vue'),
        meta: {
          title: '使用详情',
          isHidden: true,
          breadcrumb: ['用户目录', '使用详情'],
        },
      },
      {
        path: 'usage/:id/capacity-prediction',
        name: 'UsageCapacityPrediction',
        component: () => import('@/pages/capacity-prediction/CapacityPredictionDetailPage.vue'),
        props: { assetType: 'storage_usage', listRouteName: 'CapacityPredictions', listLabel: '容量预测' },
        meta: {
          title: '容量预测',
          isHidden: true,
          breadcrumb: ['用户目录', '容量预测'],
        },
      },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: 'capacity-predictions',
        name: 'CapacityPredictions',
        component: () => import('@/pages/capacity-prediction/CapacityPredictionListPage.vue'),
        meta: {
          title: '容量预测',
          isRoot: true,
          menuOrder: 40,
          icon: 'i-ri-line-chart-line',
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
          icon: 'i-ri-briefcase-4-line',
        },
      },
      {
        path: '/project/:id',
        name: 'ProjectDetail',
        component: () => import('@/pages/project/ProjectDetailPage.vue'),
        meta: {
          title: '项目详情',
          isHidden: true,
          breadcrumb: ['项目', '项目详情'],
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
          isHidden: true,
          icon: 'i-ri-team-line',
        },
      },
      {
        path: 'group/:id',
        name: 'GroupDetail',
        component: () => import('@/pages/group/GroupDetailPage.vue'),
        meta: {
          title: '项目组详情',
          isHidden: true,
          breadcrumb: ['项目组', '项目组详情'],
        },
      },
      {
        path: 'group/:id/capacity-prediction',
        name: 'GroupCapacityPrediction',
        component: () => import('@/pages/capacity-prediction/CapacityPredictionDetailPage.vue'),
        props: { assetType: 'group', listRouteName: 'CapacityPredictions', listLabel: '容量预测' },
        meta: {
          title: '容量预测',
          isHidden: true,
          breadcrumb: ['项目组', '容量预测'],
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
          icon: 'i-ri-notification-3-line',
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
          icon: 'i-ri-robot-2-line',
        },
      },
    ],
  },
  {
    path: '/admin',
    component: AppLayout,
    meta: {
      title: '系统管理',
      icon: 'i-ri-settings-3-line',
      isRoot: true,
      menuOrder: 70,
      // isAccessible: () => hasRole('diskpulse:admin') ? 200 : 403,
      isAccessible: () => hasRole('superadmin') ? 200 : 403,
    },
    children: [
      {
        path: '',
        meta: {
          title: '存储集群',
          icon: 'i-ri-server-line',
          menuKey: 'admin-storage-resources',
        },
        children: [
          {
            path: 'storage-clusters',
            name: 'StorageClusters',
            component: () => import('@/pages/admin/storage-cluster/StorageClusterListPage.vue'),
            meta: {
              title: '集群列表',
              icon: 'i-ri-server-line',
            },
          },
          {
            path: 'aggregates',
            name: 'Aggregates',
            component: () => import('@/pages/admin/aggregate/AggregateListPage.vue'),
            meta: {
              title: '容量池',
              icon: 'i-ri-pie-chart-2-line',
            },
          },
          {
            path: 'volumes',
            name: 'Volumes',
            component: () => import('@/pages/admin/volume/VolumeListPage.vue'),
            meta: {
              title: '存储空间',
              icon: 'i-ri-database-2-line',
            },
          },
          {
            path: 'qtrees',
            name: 'Qtrees',
            component: () => import('@/pages/admin/qtree/QtreeListPage.vue'),
            meta: {
              title: 'Qtree（NetApp）',
              icon: 'i-ri-folder-2-line',
            },
          },
        ],
      },
      {
        path: 'storage-cluster/:id',
        name: 'StorageClusterDetail',
        component: () => import('@/pages/admin/storage-cluster/StorageClusterDetailPage.vue'),
        meta: {
          title: '存储集群详情',
          isHidden: true,
          breadcrumb: ['系统管理', '存储集群', '存储集群详情'],
        },
      },
      {
        path: 'aggregate/:id',
        name: 'AggregateDetail',
        component: () => import('@/pages/admin/aggregate/AggregateDetailPage.vue'),
        meta: {
          title: '容量池详情',
          isHidden: true,
          breadcrumb: ['系统管理', '容量池', '容量池详情'],
        },
      },
      {
        path: 'volume/:id',
        name: 'VolumeDetail',
        component: () => import('@/pages/admin/volume/VolumeDetailPage.vue'),
        meta: {
          title: '存储空间详情',
          isHidden: true,
          breadcrumb: ['系统管理', '存储空间', '存储空间详情'],
        },
      },
      {
        path: 'group-tags',
        name: 'GroupTags',
        component: () => import('@/pages/group-tag/GroupTagListPage.vue'),
        meta: {
          title: '项目组标签',
          icon: 'i-ri-price-tag-3-line',
        },
      },
      {
        path: 'qtree/:id',
        name: 'QtreeDetail',
        component: () => import('@/pages/admin/qtree/QtreeDetailPage.vue'),
        meta: {
          title: 'Qtree（NetApp）详情',
          isHidden: true,
          breadcrumb: ['系统管理', 'Qtree（NetApp）', 'Qtree（NetApp）详情'],
        },
      },
      {
        path: 'users',
        name: 'UsersManagement',
        component: () => import('@/pages/admin/user/UserListPage.vue'),
        meta: {
          title: '用户信息管理',
          icon: 'i-ri-team-line',
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
          icon: 'i-ri-settings-3-line',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'ai-center',
        name: 'AICenter',
        component: () => import('@/pages/admin/ai/AiCenterPage.vue'),
        meta: {
          title: 'AI 中心',
          icon: 'i-ri-robot-2-line',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'forecast-governance',
        name: 'ForecastGovernance',
        component: () => import('@/pages/admin/forecast-governance/ForecastGovernancePage.vue'),
        meta: {
          title: '容量预测治理', icon: 'i-ri-line-chart-line',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'incidents',
        name: 'IncidentCenter',
        component: () => import('@/pages/incident/IncidentCenterPage.vue'),
        meta: {
          title: '事件中心',
          icon: 'i-ri-alarm-warning-line',
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
          breadcrumb: ['系统管理', 'AI 中心', 'AI 审计详情'],
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'audit-events',
        name: 'AuditEvents',
        component: () => import('@/pages/admin/audit/AuditEventListPage.vue'),
        meta: {
          title: '统一操作审计',
          icon: 'i-ri-file-search-line',
          isAccessible: () => hasRole('superadmin') ? 200 : 403,
        },
      },
      {
        path: 'audit-events/:id',
        name: 'AuditEventDetail',
        component: () => import('@/pages/admin/audit/AuditEventDetailPage.vue'),
        meta: {
          title: '审计事件详情',
          isHidden: true,
          breadcrumb: ['系统管理', '统一操作审计', '审计事件详情'],
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
