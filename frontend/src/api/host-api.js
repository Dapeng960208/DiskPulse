import BaseApi from './support/crud-api';

class HostApi extends BaseApi {
  fetchResource(hostId,queryParams){
    return super.get(`/${hostId}/resource`,queryParams)
  }

  fetchSummary(hostId){
    return super.get(`/${hostId}/summary`)
  }
}

export default new HostApi('/hosts/');
