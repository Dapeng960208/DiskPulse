import CrudApi from './support/crud-api';

class StorageClusterApi extends CrudApi {
  fetchStorageRealTimeDataById(id, queryParams) {
    return super.get(`/${id}/realtime`, queryParams);
  }

  fetchCapacityChange(id, queryParams) {
    return super.get(`/${id}/analytics/capacity-change`, queryParams);
  }

  fetchErrorSeverity(id, queryParams) {
    return super.get(`/${id}/analytics/error-severity`, queryParams);
  }

  fetchTopLatency(id, queryParams) {
    return super.get(`/${id}/analytics/top-latency`, queryParams);
  }

  fetchRepeatedFaults(id, queryParams) {
    return super.get(`/${id}/analytics/repeated-faults`, queryParams);
  }

  exportAnalytics(id, queryParams) {
    return super.export(`/${id}/analytics/export`, queryParams);
  }
}

export default new StorageClusterApi('/storage-clusters/');
