import BaseApi from './support/crud-api';

class AggregateApi extends BaseApi {
  fetchAggregateTrees(queryParams){
    return super.get(`/storage-trees/`,queryParams)
  }
  fetchAggregateTreeById(aggregateId,queryParams){
    return super.get(`/${aggregateId}/storage-tree`,queryParams)
  }
  fetchStorageRealTimeDataById(qtreeId,queryParams){
    return super.get(`/${qtreeId}/realtime`,queryParams)
  }
}

export default new AggregateApi('/aggregates/');
