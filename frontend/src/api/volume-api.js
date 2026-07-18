import BaseApi from './support/crud-api';

class VolumeApi extends BaseApi {
  fetchStorageRealTimeDataById(qtreeId,queryParams){
    return super.get(`/${qtreeId}/realtime`,queryParams)
  }

  fetchMonitoring(id, queryParams) {
    return super.get(`/${id}/monitoring`, queryParams);
  }
}

export default new VolumeApi('/volumes/');
