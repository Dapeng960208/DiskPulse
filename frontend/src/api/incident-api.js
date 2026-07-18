import BaseApi from './support/base-api';

class IncidentApi extends BaseApi {
  fetchForecasts(queryParams) {
    return super.get('/forecasts', queryParams);
  }

  fetchAnomalies(queryParams) {
    return super.get('/anomalies', queryParams);
  }

  fetchIncidents(queryParams) {
    return super.get('/incidents', queryParams);
  }

  fetchIncident(id) {
    return super.get(`/incidents/${id}`);
  }

  fetchDiagnosis(id) {
    return super.get(`/incidents/${id}/diagnosis`);
  }

  updateIncident(id, payload) {
    return super.patch(`/incidents/${id}`, payload);
  }

  createComment(id, payload) {
    return super.post(`/incidents/${id}/comments`, payload);
  }

  createMaintenanceWindow(payload) {
    return super.post('/maintenance-windows', payload);
  }
}

export default new IncidentApi('/v1');
