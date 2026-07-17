import BaseApi from './support/crud-api';

const storageAlertThresholdApi = new BaseApi('/config/storage-alert-thresholds');

class ConfigApi extends BaseApi {
  updateConfig(queryParams) {
    return super.put('',queryParams);
  }

  fetchStorageAlertThresholds() {
    return storageAlertThresholdApi.fetch();
  }
}

export default new ConfigApi('/config/storage');


