import CrudApi from './support/crud-api';

class StorageClusterApi extends CrudApi {
  fetchStorageRealTimeDataById(id, queryParams) {
    return super.get(`/${id}/realtime`, queryParams);
  }
}

export default new StorageClusterApi('/storage-clusters/');
