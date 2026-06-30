<script setup>
defineProps({
  cols: {
    type: [Number, String],
    validator: (value) => (typeof value) === 'number' || value === 'auto',
    default: 4,
  },
  minColWidth: {
    type: String,
    default: '240px',
  },
  tailJustify: {
    type: String,
    validator: (value) => ['start', 'end', 'center', 'stretch'].includes(value),
    default: 'end',
  },
});
</script>

<template>
  <div
    class="grid-container"
    :style="{
      '--grid-min-column-width': minColWidth,
      '--grid-template-columns': cols === 'auto' ? `repeat(auto-fit, minmax(min(100%, var(--grid-min-column-width)), 1fr))` : `repeat(${cols}, minmax(0, 1fr))`,
      '--grid-tail-column': cols === 'auto' ? '-2 / span 1' : `${cols} / span 1`,
    }"
  >
    <slot></slot>
    <div
      class="grid-tail"
      :style="{
        justifySelf: tailJustify,
        '--grid-tail-column': cols === 'auto' ? '-2 / span 1' : `${cols} / span 1`,
      }">
      <slot name="tail"></slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.grid-container {
  width: 100%;
  display: grid;
  grid-template-columns: var(--grid-template-columns);
  align-items: center; /* 垂直居中 */

  .grid-tail {
    grid-column: var(--grid-tail-column);
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .grid-container {
    grid-template-columns: minmax(0, 1fr);

    .grid-tail {
      grid-column: 1 / -1;
      justify-self: stretch !important;
    }
  }
}
</style>
