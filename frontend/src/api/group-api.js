import BaseApi from './support/crud-api';

class GroupApi extends BaseApi {
  fetchStorageRealTimeDataById(groupId,queryParams){
    return super.get(`/${groupId}/realtime`,queryParams)
  }
}

export default new GroupApi('/groups/');
