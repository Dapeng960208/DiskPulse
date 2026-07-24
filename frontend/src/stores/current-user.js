import { defineStore } from 'pinia';
import { getBrowserTimeZone, setPresentationTimeZone } from '@/utils/datetime.js';

export const useCurrentUser = defineStore('currentUser', {
  state: () => ({
    id: null,
    avatarUrl: '',
    displayName: '',
    roleCodes: [],
    permissions: [],
    extensionAttributes: null,
    timeZone: 'Asia/Shanghai',
  }),
  actions: {
    setCurrentUser(account) {
      const {
        id, avatarUrl, commonName, roleCodes, permissionCodes, extensionAttributes, time_zone: timeZone,
      } = account;
      this.id = id;
      this.avatarUrl = avatarUrl;
      this.displayName = commonName;
      this.roleCodes = roleCodes;
      this.extensionAttributes = extensionAttributes;
      this.timeZone = timeZone || getBrowserTimeZone();
      setPresentationTimeZone(this.timeZone);
      this.permissions = permissionCodes.map((permissionCode) => {
        const [applicationName, resourceName, operationName] = permissionCode;

        return {
          applicationName,
          resourceName,
          operationName,
        };
      });
    },
  },
});
