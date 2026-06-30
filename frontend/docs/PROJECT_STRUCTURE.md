# StoragePulse - 项目结构规范文档

## 📋 目录

- [项目概述](#项目概述)
- [核心功能模块](#核心功能模块)
- [目录结构](#目录结构)
- [路由规范](#路由规范)
- [权限控制](#权限控制)
- [API 规范](#api-规范)
- [组件规范](#组件规范)
- [开发规范](#开发规范)

---

## 项目概述

**项目名称**: StoragePulse  
**项目简介**: 专为芯片行业设计的存储资源监控与管理平台，基于 NetApp 存储架构  
**技术栈**: Vue 3 + Vite + Element Plus + Vue Router + Pinia  
**版本**: v1.0.0

### 系统架构

```
StoragePulse 存储管理平台
├── 普通用户功能（无需特殊权限）
│   ├── 概览 Dashboard
│   ├── 用户存储管理
│   ├── 项目管理
│   ├── 项目组管理
│   └── 告警管理
└── 管理员功能（需要 diskpulse:admin 角色）
    ├── 存储一览
    ├── 聚合管理（Aggregate）
    ├── Volume 管理
    ├── Qtree 管理
    ├── 账号管理
    ├── 离职备份
    └── 系统设置
```

---

## 核心功能模块

### 1. 普通用户功能

| 功能模块 | 路由路径 | 说明 |
|---------|---------|------|
| 概览 | `/` | 系统概览页面，展示关键指标 |
| 用户存储 | `/usage` | 查看和管理用户存储使用情况 |
| 项目管理 | `/projects` | 项目列表和详情管理 |
| 项目组管理 | `/groups` | 项目组列表和详情管理 |
| 告警管理 | `/alerts` | 查看系统告警信息 |

### 2. 管理员功能

| 功能模块 | 路由路径 | 权限要求 | 说明 |
|---------|---------|---------|------|
| 存储一览 | `/admin/dashboard` | diskpulse:admin | NetApp 存储系统总览 |
| 聚合管理 | `/admin/aggregates` | diskpulse:admin | Aggregate 资源管理 |
| Volume 管理 | `/admin/volumes` | diskpulse:admin | Volume 资源管理 |
| Qtree 管理 | `/admin/qtrees` | diskpulse:admin | Qtree 资源管理 |
| 账号管理 | `/admin/users` | diskpulse:admin | 用户账号管理 |
| 离职备份 | `/admin/backup` | diskpulse:admin | 离职人员数据备份 |
| 系统设置 | `/admin/settings` | diskpulse:admin | 系统配置管理 |

---

## 目录结构

```
diskpulse/
├── docs/                         # 项目文档
│   ├── PROJECT_STRUCTURE.md      # 项目结构规范（本文档）
│   └── UI_DESIGN_GUIDE.md        # UI 设计规范
│
├── src/
│   ├── api/                      # API 接口层
│   │   ├── support/              # API 基础支持
│   │   │   ├── base-api.js       # API 基类
│   │   │   ├── base-request.js   # 请求基类
│   │   │   ├── crud-api.js       # CRUD API 基类
│   │   │   └── request-builder.js # 请求构建器
│   │   ├── users-api.js          # 用户 API（含登录/登出/获取用户信息）
│   │   ├── aggregate-api.js      # 聚合 API
│   │   ├── volume-api.js         # Volume API
│   │   ├── qtree-api.js          # Qtree API
│   │   ├── project-api.js        # 项目 API
│   │   ├── group-api.js          # 项目组 API
│   │   ├── storage-usage-api.js  # 存储使用 API
│   │   ├── alert-api.js          # 告警 API
│   │   └── config-api.js         # 配置 API
│   │
│   ├── assets/                   # 静态资源
│   │   └── logo.png              # 系统 Logo
│   │
│   ├── common/                   # 公共组件
│   │   └── charts/               # 图表组件
│   │       ├── AnimatedTextChart.vue
│   │       ├── BarStackChart.vue
│   │       ├── DiskUsage.vue
│   │       ├── LineCharts.vue
│   │       └── PieCharts.vue
│   │
│   ├── components/               # 业务组件
│   │   ├── basic/                # 基础组件
│   │   │   ├── AppLink.vue
│   │   │   ├── GridContainer.vue
│   │   │   └── ThemeSwitch.vue
│   │   ├── data/                 # 数据展示组件
│   │   │   ├── DataTable.vue
│   │   │   ├── Result.vue
│   │   │   └── UserAvatar.vue
│   │   └── form/                 # 表单组件
│   │       ├── QueryForm.vue
│   │       ├── FormDialog.vue
│   │       ├── ExportDialog.vue
│   │       └── ...Select.vue     # 各种选择器组件
│   │
│   ├── composables/              # 组合式函数
│   │   ├── common.js             # 通用组合函数
│   │   ├── dialog.js             # 对话框组合函数
│   │   ├── form.js               # 表单组合函数
│   │   └── query.js              # 查询组合函数
│   │
│   ├── layouts/                  # 布局组件
│   │   ├── AppLayout.vue         # 主布局
│   │   └── components/           # 布局子组件
│   │       ├── AppHeader.vue     # 顶部导航
│   │       ├── AppFooter.vue     # 底部信息
│   │       ├── RouteMenu.vue     # 路由菜单
│   │       └── RouteMenuItem.vue # 菜单项
│   │
│   ├── pages/                    # 页面组件
│   │   ├── auth/                 # 认证页面
│   │   │   └── LoginPage.vue     # 登录页
│   │   │
│   │   ├── dashboard/            # 概览页面
│   │   │   └── DashboardPage.vue
│   │   │
│   │   ├── usage/                # 用户存储管理（普通用户）
│   │   │   ├── UsageListPage.vue
│   │   │   ├── UsageDetailPage.vue
│   │   │   └── components/
│   │   │
│   │   ├── project/              # 项目管理（普通用户）
│   │   │   ├── ProjectListPage.vue
│   │   │   ├── ProjectDetailPage.vue
│   │   │   └── components/
│   │   │
│   │   ├── group/                # 项目组管理（普通用户）
│   │   │   ├── GroupListPage.vue
│   │   │   ├── GroupDetailPage.vue
│   │   │   └── components/
│   │   │
│   │   ├── alert/                # 告警管理（普通用户）
│   │   │   └── AlertListPage.vue
│   │   │
│   │   ├── admin/                # 管理员功能（需要权限）
│   │   │   ├── dashboard/        # 存储一览
│   │   │   │   └── DashboardPage.vue
│   │   │   ├── aggregate/        # 聚合管理
│   │   │   │   ├── AggregateListPage.vue
│   │   │   │   └── AggregateDetailPage.vue
│   │   │   ├── volume/           # Volume 管理
│   │   │   │   ├── VolumeListPage.vue
│   │   │   │   └── VolumeDetailPage.vue
│   │   │   ├── qtree/            # Qtree 管理
│   │   │   │   ├── QtreeListPage.vue
│   │   │   │   └── QtreeDetailPage.vue
│   │   │   ├── user/             # 账号管理
│   │   │   │   ├── UserListPage.vue
│   │   │   │   └── components/
│   │   │   ├── backup/           # 离职备份
│   │   │   │   └── BackUpListPage.vue
│   │   │   └── settings/         # 系统设置
│   │   │       └── SettingsPage.vue
│   │   │
│   │   └── error/                # 错误页面
│   │       ├── NotFoundPage.vue  # 404
│   │       └── UnauthorizedPage.vue # 403
│   │
│   ├── router/                   # 路由配置
│   │   ├── index.js              # 路由实例和守卫
│   │   └── routes.js             # 路由定义
│   │
│   ├── stores/                   # 状态管理
│   │   ├── app-settings.js       # 应用设置
│   │   └── current-user.js       # 当前用户信息
│   │
│   ├── styles/                   # 样式文件
│   │   ├── style.scss            # 全局样式
│   │   ├── variables.scss        # CSS 变量
│   │   ├── mixins.scss           # SCSS Mixins
│   │   └── animation.css         # 动画样式
│   │
│   ├── utils/                    # 工具函数
│   │   ├── authorization.js      # 权限工具
│   │   ├── common.js             # 通用工具
│   │   ├── colorUtils.js         # 颜色工具
│   │   ├── validate.js           # 验证工具
│   │   └── index.js              # 工具导出
│   │
│   ├── App.vue                   # 根组件
│   └── main.js                   # 入口文件
│
├── .env                          # 开发环境变量
├── .env.production               # 生产环境变量
├── .env.test                     # 测试环境变量
├── vite.config.js                # Vite 配置
├── package.json                  # 项目依赖
└── README.md                     # 项目说明
```

---

## 路由规范

### 路由命名规则

1. **普通用户路由**: 直接挂载在根路径 `/` 下
2. **管理员路由**: 统一使用 `/admin` 前缀
3. **详情页路由**: 使用 `/:id` 动态参数

### 路由配置示例

```javascript
// 普通用户路由
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
        icon: 'i-ri-user-line',
      },
    },
  ],
}

// 管理员路由
{
  path: '/admin',
  component: AppLayout,
  meta: {
    title: '系统管理',
    icon: 'i-ri-settings-line',
    isRoot: true,
    isAccessible: () => hasRole('diskpulse:admin') ? 200 : 403,
  },
  children: [
    {
      path: 'dashboard',
      name: 'AdminDashboard',
      component: () => import('@/pages/admin/dashboard/DashboardPage.vue'),
      meta: {
        title: '存储一览',
      },
    },
  ],
}
```

### 路由元信息 (meta)

| 字段 | 类型 | 说明 |
|-----|------|------|
| `title` | String | 页面标题 |
| `isRoot` | Boolean | 是否为根级菜单项 |
| `isHidden` | Boolean | 是否在菜单中隐藏 |
| `isPublic` | Boolean | 是否为公开页面（无需登录） |
| `icon` | String | 菜单图标（UnoCSS 图标类名） |
| `isAccessible` | Function | 权限检查函数，返回 200/403/404 |

---

## 权限控制

### 角色定义

| 角色代码 | 说明 | 权限范围 |
|---------|------|---------|
| `diskpulse:admin` | 管理员 | 可访问所有管理员功能 |
| `*:root` | 超级管理员 | 拥有所有权限 |

### 权限检查函数

```javascript
import { hasRole, hasPermission } from '@/utils/authorization';

// 检查角色
hasRole('diskpulse:admin')

// 检查权限
hasPermission('diskpulse:user:read')

// 检查任意角色
hasAnyRole(['diskpulse:admin', 'diskpulse:user'])

// 检查所有角色
hasAllRoles(['diskpulse:admin', 'diskpulse:user'])
```

### 路由守卫

路由守卫在 `src/router/index.js` 中配置：

```javascript
router.beforeEach(async (to, from) => {
  // 1. 公开页面直接放行
  if (to.meta.isPublic) return;
  
  // 2. 获取用户信息
  const { result } = await usersApi.fetchProfile();
  currentUser.setCurrentUser(result);
  
  // 3. 检查页面访问权限
  if (to.meta.isAccessible) {
    const resultCode = to.meta.isAccessible();
    if (resultCode === 403) return '/403';
    if (resultCode === 404) return '/404';
  }
});
```

---

## API 规范

### API 文件组织

所有 API 文件放在 `src/api/` 目录下，按功能模块划分：

```
src/api/
├── support/              # API 基础支持
├── users-api.js          # 用户相关（登录、登出、用户信息）
├── aggregate-api.js      # 聚合管理
├── volume-api.js         # Volume 管理
├── qtree-api.js          # Qtree 管理
├── project-api.js        # 项目管理
├── group-api.js          # 项目组管理
├── storage-usage-api.js  # 存储使用
├── alert-api.js          # 告警管理
└── config-api.js         # 配置管理
```

### API 类定义

```javascript
import CrudApi from './support/crud-api';

class UsersApi extends CrudApi {
  /**
   * 用户登录
   */
  login(username, password) {
    return super.post('/login', { username, password });
  }

  /**
   * 用户登出
   */
  logout() {
    return super.post('/logout');
  }

  /**
   * 获取当前登录用户信息
   */
  fetchProfile() {
    return super.get('/current/profile', null, {
      errorHandlerDisabled: true,
    });
  }
}

export default new UsersApi('/users');
```

### API 调用示例

```javascript
import usersApi from '@/api/users-api';

// 登录
const { result } = await usersApi.login(username, password);

// 获取用户信息
const { result: userProfile } = await usersApi.fetchProfile();

// 登出
await usersApi.logout();
```

---

## 组件规范

### 组件分类

1. **页面组件** (`src/pages/`): 完整的页面视图
2. **布局组件** (`src/layouts/`): 页面布局结构
3. **业务组件** (`src/components/`): 可复用的业务组件
4. **公共组件** (`src/common/`): 通用组件（如图表）

### 组件命名规范

- **页面组件**: `XxxPage.vue` (如 `UserListPage.vue`)
- **对话框组件**: `XxxDialog.vue` (如 `UserFormDialog.vue`)
- **表单组件**: `XxxForm.vue` (如 `UserForm.vue`)
- **表格组件**: `XxxTable.vue` (如 `UserTable.vue`)
- **选择器组件**: `XxxSelect.vue` (如 `UserSelect.vue`)

### 组件结构

```vue
<script setup>
// 1. 导入依赖
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';

// 2. 定义 props 和 emits
const props = defineProps({
  // ...
});

const emit = defineEmits(['update', 'delete']);

// 3. 响应式数据
const loading = ref(false);
const data = ref([]);

// 4. 计算属性
const filteredData = computed(() => {
  // ...
});

// 5. 方法
function handleClick() {
  // ...
}

// 6. 生命周期
onMounted(() => {
  // ...
});
</script>

<template>
  <!-- 模板内容 -->
</template>

<style lang="scss" scoped>
/* 样式 */
</style>
```

---

## 开发规范

### 代码风格

1. **使用 ESLint**: 遵循项目 `.eslintrc.cjs` 配置
2. **使用 Composition API**: 优先使用 `<script setup>` 语法
3. **TypeScript**: 可选，但推荐在关键模块使用类型注解
4. **命名规范**:
   - 组件: PascalCase (`UserList.vue`)
   - 文件: kebab-case (`user-list.js`)
   - 变量/函数: camelCase (`getUserList`)
   - 常量: UPPER_SNAKE_CASE (`API_BASE_URL`)

### Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
feat(auth): 添加用户登录功能

- 实现登录表单验证
- 集成 users-api 登录接口
- 添加登录状态管理

Closes #123
```

### 环境变量

项目使用三个环境配置文件：

| 文件 | 环境 | 说明 |
|-----|------|------|
| `.env` | 开发环境 | 本地开发使用 |
| `.env.test` | 测试环境 | 测试服务器使用 |
| `.env.production` | 生产环境 | 生产服务器使用 |

**环境变量命名规范**:
- 必须以 `VITE_` 开头
- 使用 UPPER_SNAKE_CASE 命名

**示例**:
```bash
VITE_APP_TITLE = 'StoragePulse'
VITE_APP_API_BASE_URL = 'https://api.example.com/api'
VITE_REQUEST_TIMEOUT = 30000
```

### 构建和部署

```bash
# 开发环境
pnpm dev

# 测试环境构建
pnpm build:test

# 生产环境构建
pnpm build:prod

# 预览构建结果
pnpm preview
```

---

## 技术栈版本

- Vue: 3.x
- Vite: 4.x
- Element Plus: 2.x
- Vue Router: 4.x
- Pinia: 2.x
- UnoCSS: 0.x

## 相关文档

- [Vue 3 官方文档](https://vuejs.org/)
- [Element Plus 文档](https://element-plus.org/)
- [Vue Router 文档](https://router.vuejs.org/)
- [Pinia 文档](https://pinia.vuejs.org/)
- [UnoCSS 文档](https://unocss.dev/)
- [NetApp 官方文档](https://docs.netapp.com/)

---

**文档维护**: 请在项目结构发生重大变更时及时更新本文档。

**最后更新**: 2026-03-26
