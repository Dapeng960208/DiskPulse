import { defineStore } from 'pinia';

export const useCurrentUser = defineStore('currentUser', {
  state: () => ({
    id: null,
    avatarUrl: '',
    displayName: '',
    roleCodes: [],
    permissions: [],
    extensionAttributes:null
  }),
  actions: {
    setCurrentUser(account) {
      const { id, avatarUrl, commonName, roleCodes, permissionCodes,extensionAttributes } = account;
      this.id = id;
      this.avatarUrl = avatarUrl;
      this.displayName = commonName;
      this.roleCodes = roleCodes;
      this.extensionAttributes = extensionAttributes;
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
