import BaseApi from './support/crud-api';

class ProjectApi extends BaseApi {
  fetchStorageRealTimeDataById(projectId,queryParams){
    return super.get(`/${projectId}/storage`,queryParams)
  }
  fetchStorageSummary(queryParams){
    return super.get(`/storage/summary`,queryParams)
  }
  fetchStorageTreeById(projectId,queryParams){
    return super.get(`/${projectId}/storage-tree`,queryParams)
  }
  fetchGroupStorage(queryParams){
    return super.get(`/storage/groups`,queryParams)
  }
}

export default new ProjectApi('/projects/');
