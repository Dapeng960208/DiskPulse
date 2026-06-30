import authRequest from './support/auth-request';
import CrudApi from './support/crud-api';

class AccountApi extends CrudApi {
  /**
   * 获取用户信息，包含角色等
   * @param {Number} id
   */
  fetchProfile(id) {
    return id
      ? super.get(`/${id}/profile`)
      : super.get('/current/profile', null, {
        errorHandlerDisabled: true,
      });
  }
}

export default new AccountApi('/accounts/', authRequest);
