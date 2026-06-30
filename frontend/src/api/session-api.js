import BaseApi from './support/base-api';
import authRequest from './support/auth-request';

class SessionApi extends BaseApi {
  login(username, password) {
    return super.post('', { username, password });
  }

  logout() {
    return super.delete('');
  }
}

export default new SessionApi('/sessions', authRequest);
