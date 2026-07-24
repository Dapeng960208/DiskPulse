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
   * 获取当前登录用户信息（含角色、权限）
   */
  fetchProfile() {
    return super.get('/current/profile', null, {
      errorHandlerDisabled: true,
    });
  }

  updateCurrentProfile(data) {
    return super.patch('/current/profile', data);
  }

  fetchTimeZones() {
    return super.get('/current/time-zones');
  }

  syncLdap() {
    return super.post('/sync-ldap');
  }

  /**
   * 获取指定用户摘要信息
   */
  fetchSummaryById(userId, queryParams) {
    return super.get(`/${userId}/summary`, queryParams);
  }
}

export default new UsersApi('/users');
