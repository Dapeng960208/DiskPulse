import { createPinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import { vi } from 'vitest';

const darkMode = ref(false);
const asideCollapsed = ref(false);

vi.mock('@vueuse/core', () => ({
  useDark: () => darkMode,
  useToggle: (target) => {
    if (target) {
      return () => {
        target.value = !target.value;
        return target.value;
      };
    }

    const local = ref(false);
    return [
      local,
      () => {
        local.value = !local.value;
        return local.value;
      },
    ];
  },
}));

const { useAppSettings } = await import('@/stores/app-settings');
const { useCurrentUser } = await import('@/stores/current-user');

describe('stores', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    darkMode.value = false;
    asideCollapsed.value = false;
  });

  it('toggles app settings state', () => {
    const store = useAppSettings();

    expect(store.theme).toBe('light');
    store.toggleTheme();
    expect(store.theme).toBe('dark');

    expect(store.asideCollapsed).toBe(false);
    store.toggleAsideCollapsed();
    expect(store.asideCollapsed).toBe(true);
  });

  it('maps current user fields into store state', () => {
    const store = useCurrentUser();

    store.setCurrentUser({
      id: 2,
      avatarUrl: 'avatar.png',
      commonName: 'DiskPulse User',
      roleCodes: ['diskpulse:admin'],
      permissionCodes: [['diskpulse', 'users', 'read']],
      extensionAttributes: { org: 'storage' },
    });

    expect(store.id).toBe(2);
    expect(store.displayName).toBe('DiskPulse User');
    expect(store.roleCodes).toEqual(['diskpulse:admin']);
    expect(store.permissions).toEqual([
      { applicationName: 'diskpulse', resourceName: 'users', operationName: 'read' },
    ]);
  });
});
