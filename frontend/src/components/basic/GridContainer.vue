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
      gridTemplateColumns: cols === 'auto' ? `repeat(auto-fill, minmax(${minColWidth}, 1fr))` : `repeat(${cols}, 1fr)`,
    }"
  >
    <slot></slot>
    <div :style="{ gridColumn: `-2 / span 1`, justifySelf: tailJustify }">
      <slot name="tail"></slot>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.grid-container {
  width: 100%;
  display: grid;
  align-items: center; /* 垂直居中 */
}
</style>
