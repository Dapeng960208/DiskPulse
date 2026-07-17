<script setup>
import { ElFooter } from 'element-plus';

defineProps({
  height: {
    type: String,
    default: '40px',
  },
});

const currentYear = new Date().getFullYear();
</script>

<template>
  <ElFooter class="app-footer">
    <div class="copyright">
      <small>
        版权所有 ©2021-{{ currentYear }} 智能应用部 保留一切权利
      </small>
    </div>
  </ElFooter>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.app-footer {
  height: v-bind(height);
  flex: 0 0 v-bind(height);
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 var(--spacing-2xl);
  border-top: 1px solid var(--border-light);
  background: var(--bg-primary);

  .copyright {
    text-align: center;

    small {
      font-size: var(--font-size-xs);
      color: var(--text-tertiary);
      letter-spacing: 0.025em;

      a {
        color: var(--text-tertiary);
        text-decoration: none;
        transition: var(--transition-base);

        &:hover {
          color: var(--primary-color);
        }
      }
    }
  }
}
</style>
