import BaseApi from './support/base-api';

class CapacityPredictionApi extends BaseApi {
  visibility() { return this.get('/capacity-predictions/visibility'); }
  fetchPredictions(queryParams) { return this.get('/capacity-predictions', queryParams); }
  access(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}/access`); }
  fetchPrediction(assetType, assetId, config) {
    const path = `/capacity-predictions/${assetType}/${assetId}`;
    return config ? this.get(path, undefined, config) : this.get(path);
  }
  fetchRisk(assetType, assetId, config) {
    const path = `/capacity-predictions/${assetType}/${assetId}/risk`;
    return config ? this.get(path, undefined, config) : this.get(path);
  }
  fetchPlans(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}/plans`); }
  fetchRelatedIncidents(assetType, assetId, config) {
    const path = `/capacity-predictions/${assetType}/${assetId}/related-incidents`;
    return config ? this.get(path, undefined, config) : this.get(path);
  }
  createPlan(assetType, assetId, payload) { return this.post(`/capacity-predictions/${assetType}/${assetId}/plans`, payload); }
  settings() { return this.get('/admin/capacity-prediction-settings'); }
  updateSettings(payload) { return this.patch('/admin/capacity-prediction-settings', payload); }
  fetchCandidates() { return this.get('/admin/capacity-prediction-candidates'); }
  createCandidate(payload) { return this.post('/admin/capacity-prediction-candidates', payload); }
  activateCandidate(candidateId) { return this.post(`/admin/capacity-prediction-candidates/${candidateId}/activate`); }
}

export default new CapacityPredictionApi('/v1');
