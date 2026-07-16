import BaseApi from './support/crud-api';

class GroupApi extends BaseApi {
  fetchStorageRealTimeDataById(groupId,queryParams){
    return super.get(`/${groupId}/realtime`,queryParams)
  }

  adjustQuota(groupId, data) {
    return super.patch(`/${groupId}/quota`, data);
  }
}

export default new GroupApi('/groups/');
