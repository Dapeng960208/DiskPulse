import authRequest from './support/auth-request';
import CrudApi from './support/crud-api';

class DomainGroup extends CrudApi {
  /**
   * 获取群组信息，包含等
   */

}

export default new DomainGroup('/groups', authRequest);
