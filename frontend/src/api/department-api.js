import authRequest from './support/auth-request';
import CrudApi from './support/crud-api';

class DepartmentApi extends CrudApi {
  fetchTopLevel() {
    return super.get('/top-level');
  }
}

export default new DepartmentApi('/departments/', authRequest);
