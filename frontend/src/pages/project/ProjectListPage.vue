<script setup>
import ProjectTable from './components/ProjectTable.vue';
</script>

<template>
  <section class="project-list-page">
    <ProjectTable class="project-list-page__table" />
  </section>
</template>

<style scoped>
.project-list-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.project-list-page__table {
  flex: 1 1 auto;
  min-height: 0;
}
</style>
