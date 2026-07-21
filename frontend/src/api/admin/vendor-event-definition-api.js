import CrudApi from '../support/crud-api';

class VendorEventDefinitionApi extends CrudApi {
  discover() {
    return super.post('/discover');
  }
}

export default new VendorEventDefinitionApi('/admin/vendor-event-definitions');
