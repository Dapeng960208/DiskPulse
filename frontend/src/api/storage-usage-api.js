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

  adjustQuota(storageUsageId, data) {
    return super.patch(`/${storageUsageId}/quota`, data);
  }

  reconcileQuota(storageUsageId) {
    return super.post(`/${storageUsageId}/quota/reconcile`);
  }

  quotaHistory(storageUsageId) {
    return super.get(`/${storageUsageId}/quota/history`);
  }
}

export default new StorageUsageApi('/storage-usages/');
