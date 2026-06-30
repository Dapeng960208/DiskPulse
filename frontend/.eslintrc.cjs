module.exports = {
  root: true,

  env: {
    browser: true,
    node: true,
    es6: true,
  },

  parser: 'vue-eslint-parser',

  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },

  extends: [
    'plugin:vue/vue3-recommended',
  ],

  rules: {
    // 强制 Vue 组件名使用 PascalCase（包括 element-plus 组件）
    'vue/component-name-in-template-casing': ['error', 'PascalCase', {
      registeredComponentsOnly: false,
      ignores: [],
    }],
    // 关闭一些过于严格的规则
    'vue/multi-word-component-names': 'off',
    'vue/require-valid-default-prop': 'off',
    'vue/no-template-shadow': 'off',
    'vue/html-self-closing': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/multiline-html-element-content-newline': 'off',
    'vue/html-closing-bracket-newline': 'off',
    'vue/html-indent': ['error', 2],
    'vue/require-default-prop': 'off',
    'vue/no-v-html': 'off',
    // 多个属性时每个属性占一行
    'vue/max-attributes-per-line': ['error', {
      singleline: { max: 1 },
      multiline: { max: 1 },
    }],
    'vue/first-attribute-linebreak': ['error', {
      singleline: 'beside',
      multiline: 'below',
    }],
  },

  overrides: [
    {
      files: [
        '**/__tests__/*.{j,t}s?(x)',
        '**/tests/unit/**/*.spec.{j,t}s?(x)',
      ],
      env: {
        jest: true,
      },
    },
  ],
};
