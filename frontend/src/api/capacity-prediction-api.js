import BaseApi from './support/base-api';

class CapacityPredictionApi extends BaseApi {
  visibility() { return this.get('/capacity-predictions/visibility'); }
  access(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}/access`); }
  fetchPrediction(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}`); }
  fetchPlans(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}/plans`); }
  fetchRelatedIncidents(assetType, assetId) { return this.get(`/capacity-predictions/${assetType}/${assetId}/related-incidents`); }
  createPlan(assetType, assetId, payload) { return this.post(`/capacity-predictions/${assetType}/${assetId}/plans`, payload); }
  settings() { return this.get('/admin/capacity-prediction-settings'); }
  updateSettings(payload) { return this.patch('/admin/capacity-prediction-settings', payload); }
  fetchCandidates() { return this.get('/admin/capacity-prediction-candidates'); }
  createCandidate(payload) { return this.post('/admin/capacity-prediction-candidates', payload); }
  activateCandidate(candidateId) { return this.post(`/admin/capacity-prediction-candidates/${candidateId}/activate`); }
}

export default new CapacityPredictionApi('/v1');
