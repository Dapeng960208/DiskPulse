import { describe, expect, it } from 'vitest';
import { getDefaultAvatar } from '@/utils/default-avatar';

describe('default avatar selection', () => {
  it('selects the same built-in avatar for the same user identity', () => {
    expect(getDefaultAvatar('guojianpeng')).toBe(getDefaultAvatar('guojianpeng'));
  });

  it('uses a built-in avatar when the user identity is empty', () => {
    expect(getDefaultAvatar('')).toMatch(/default-avatar-(mint|peach|sky|lilac)\.gif$/);
  });
});
