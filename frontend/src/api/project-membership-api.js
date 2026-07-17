import BaseApi from './support/base-api';

class ProjectMembershipApi extends BaseApi {
  list(projectId) {
    return this.get(`/projects/${projectId}/members`);
  }

  create(projectId, payload) {
    return this.post(`/projects/${projectId}/members`, payload);
  }

  update(projectId, userId, payload) {
    return this.patch(`/projects/${projectId}/members/${userId}`, payload);
  }

  remove(projectId, userId) {
    return this.delete(`/projects/${projectId}/members/${userId}`);
  }
}

export default new ProjectMembershipApi('');
