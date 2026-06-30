import BaseApi from './support/crud-api';

class QtreeApi extends BaseApi {
  fetchStorageRealTimeDataById(qtreeId,queryParams){
    return super.get(`/${qtreeId}/realtime`,queryParams)
  }
}

export default new QtreeApi('/qtrees/');
