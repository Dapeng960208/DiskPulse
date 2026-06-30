import BaseApi from './support/crud-api';

class StorageUsageApi extends BaseApi {
  fetchStorageRealTimeDataById(storageUsageId,queryParams){
    return super.get(`/${storageUsageId}/realtime`,queryParams)
  }
  exportStorageUsages(queryParams){
    return  super.export(`/export/`,queryParams)
  }
  backUpStorageUsageById(storageUsageId){
    return super.post(`/${storageUsageId}/back-up`,{closed : false})
  }
}

export default new StorageUsageApi('/storage-usages/');
