import BaseApi from './support/base-api';

class DashboardApi extends BaseApi {
  fetchSummary(queryParams = {}) {
    return this.get('/summary', queryParams);
  }

  fetchCapacityTrend(queryParams = {}) {
    return this.get('/capacity-trend', queryParams);
  }

  fetchCapacityItems(queryParams = {}) {
    return this.get('/capacity-items', queryParams);
  }

  fetchAlertLevels(queryParams = {}) {
    return this.get('/alert-levels', queryParams);
  }

  fetchTopUsers(queryParams) {
    return this.get('/top-users', queryParams);
  }
}

export default new DashboardApi('/dashboard');
