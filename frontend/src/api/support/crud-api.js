import BaseApi from './base-api';

export default class CrudApi extends BaseApi {
  create(data, config) {
    return this.post('', data, config);
  }

  deleteById(id, config) {
    return this.delete(`/${id}`, config);
  }

  replace(id, data, config) {
    return this.put(`/${id}`, data, config);
  }

  update(id, data, config) {
    return this.patch(`/${id}`, data, config);
  }

  fetchById(id, queryParams, config) {
    return this.get(`/${id}`, queryParams, config);
  }

  fetch(queryParams, config) {
    return this.get('', queryParams, config);
  }
}
