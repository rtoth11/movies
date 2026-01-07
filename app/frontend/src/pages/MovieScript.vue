<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const script = ref("")

onMounted(async () => {
  const res = await api.get(`/movies/${route.params.id}/script`)
  script.value = res.data.script
})
</script>

<template>
  <div>
    <h1>Movie Script</h1>
    <pre class="script">{{ script }}</pre>
  </div>
</template>

<style scoped>
.script {
  white-space: pre-wrap;
  font-family: monospace;
  line-height: 1.5;
}
</style>
