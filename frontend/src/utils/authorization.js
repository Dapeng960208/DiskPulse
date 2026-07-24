import Cookies from 'js-cookie';
import { useCurrentUser } from '@/stores/current-user';
import { isArray, isString } from '@/utils/validate';

export const TOKEN_KEY = 'Authorization';


const cookieAttributes = {
  sameSite: 'Lax',
  // 生产环境强制 HTTPS，开发环境允许 HTTP（本地开发可能没有证书）
  ...(import.meta.env.PROD ? { secure: true } : {}),
};

export function hasToken() {
  const token = getToken();
  return token !== undefined && token !== null && token.trim() !== '';
}

export function getToken() {
  return Cookies.get(TOKEN_KEY);
}

export function setToken(token) {
  return Cookies.set(TOKEN_KEY, token, cookieAttributes);
}

export function removeToken() {
  // 删除的时候也必须附带和设置时相同的属性
  return Cookies.remove(TOKEN_KEY, cookieAttributes);
}

function getUserInfo() {
  return useCurrentUser();
}

function getRoles() {
  return getUserInfo().roleCodes;
}

function getPermissions() {
  return getUserInfo().permissions;
}

function isPermitted(permission, applicationName, resourceName, operationName) {
  if (
    permission.applicationName === '*'
    || permission.applicationName === applicationName
  ) {
    if (
      permission.resourceName === '*'
      || permission.resourceName === resourceName
    ) {
      if (
        permission.operationName === '*'
        || permission.operationName === operationName
      ) {
        return true;
      }
    }
  }

  return false;
}

export function isAuthenticated() {
  return getUserInfo().id !== null;
}

export function hasPermission(requiredPermission) {
  if (requiredPermission && isString(requiredPermission)) {
    const [applicationName, resourceName, operationName]
      = requiredPermission.split(':');
    const permissions = getPermissions();

    return (
      permissions.find((permission) => {
        return isPermitted(
          permission,
          applicationName,
          resourceName,
          operationName,
        );
      }) !== undefined
    );
  } else {
    return false;
  }
}

export function hasAnyPermission(requiredPermissions) {
  if (
    requiredPermissions
    && isArray(requiredPermissions)
    && requiredPermissions.length > 0
  ) {
    return requiredPermissions.some(hasPermission);
  } else {
    return false;
  }
}

export function hasAllPermissions(requiredPermissions) {
  if (
    requiredPermissions
    && isArray(requiredPermissions)
    && requiredPermissions.length > 0
  ) {
    return requiredPermissions.every(hasPermission);
  } else {
    return false;
  }
}

export function hasRole(requiredRole) {
  if (requiredRole && isString(requiredRole)) {
    const roles = getRoles();
    return roles.includes(requiredRole) || roles.includes('*:root') || roles.includes('superadmin');
  } else {
    return false;
  }
}

export function hasAnyRole(requiredRoles) {
  if (requiredRoles && isArray(requiredRoles) && requiredRoles.length > 0) {
    return requiredRoles.some(hasRole);
  } else {
    return false;
  }
}

export function hasAllRoles(requiredRoles) {
  if (requiredRoles && isArray(requiredRoles) && requiredRoles.length > 0) {
    return requiredRoles.every(hasRole);
  } else {
    return false;
  }
}
