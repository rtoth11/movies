<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const data = ref(null)

onMounted(async () => {
  const res = await api.get(`/actors/${route.params.id}`)
  data.value = res.data
})
</script>

<template>
  <div v-if="data">
    <h1>{{ data.actor.name }}</h1>

    <ul>
      <li v-for="m in data.movies" :key="m.tmdb_id">
        <router-link :to="`/movies/${m.tmdb_id}`">
          {{ m.title }}
        </router-link>
        —
        <router-link :to="`/characters/${m.character.id}`">
          {{ m.character.name }}
        </router-link>
      </li>
    </ul>
  </div>
</template>
