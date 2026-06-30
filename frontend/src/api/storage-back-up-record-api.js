import BaseApi from './support/crud-api';

class StorageBackUpRecordApi extends BaseApi {
  rollBackedBackUpStorageById(Id){
    return super.post(`/${Id}/rollback`)
  }
}

export default new StorageBackUpRecordApi('/storage-back-up-records/');
