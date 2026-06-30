import {
  isArray,
  isExternal,
  isString,
  validAlphabets,
  validEmail,
  validLowerCase,
  validUpperCase,
  validURL,
} from '@/utils/validate';

describe('utils/validate', () => {
  it('checks external links', () => {
    expect(isExternal('https://example.com')).toBe(true);
    expect(isExternal('/internal/path')).toBe(false);
  });

  it('validates URLs and email addresses', () => {
    expect(validURL('https://example.com/path')).toBe(true);
    expect(validURL('example')).toBe(false);
    expect(validEmail('user@example.com')).toBe(true);
    expect(validEmail('invalid-email')).toBe(false);
  });

  it('checks string character categories', () => {
    expect(validLowerCase('abc')).toBe(true);
    expect(validUpperCase('ABC')).toBe(true);
    expect(validAlphabets('AbCd')).toBe(true);
    expect(validLowerCase('Abc')).toBe(false);
    expect(validUpperCase('AbC')).toBe(false);
    expect(validAlphabets('abc1')).toBe(false);
  });

  it('checks runtime value types', () => {
    expect(isString('value')).toBe(true);
    expect(isString(1)).toBe(false);
    expect(isArray([])).toBe(true);
    expect(isArray({})).toBe(false);
  });
});
