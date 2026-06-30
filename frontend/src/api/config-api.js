import BaseApi from './support/crud-api';

class ConfigApi extends BaseApi {
  updateConfig(queryParams) {
    return super.put('',queryParams);
  }
}

export default new ConfigApi('/config/storage');


