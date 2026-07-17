import BaseApi from './support/base-api';

class DashboardApi extends BaseApi {
  fetchOverview(queryParams = {}) {
    return this.get('/overview', queryParams);
  }
}

export default new DashboardApi('/dashboard');
