import BaseApi from './support/base-api';

class ProjectStorageEnvironmentApi extends BaseApi {
  fetchByProject(projectId, queryParams) {
    return super.get(`/projects/${projectId}/storage-environments`, queryParams);
  }

  createForProject(projectId, data) {
    return super.post(`/projects/${projectId}/storage-environments`, data);
  }

  fetchSummaryById(id) {
    return super.get(`/storage-environments/${id}/summary`);
  }

  fetchStorageRealTimeDataById(id, queryParams) {
    return super.get(`/storage-environments/${id}/realtime`, queryParams);
  }

  replace(id, data) {
    return super.put(`/storage-environments/${id}`, data);
  }

  deleteById(id) {
    return super.delete(`/storage-environments/${id}`);
  }
}

export default new ProjectStorageEnvironmentApi('');
