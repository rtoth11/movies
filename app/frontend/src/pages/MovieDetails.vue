<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const data = ref(null)

onMounted(async () => {
  const res = await api.get(`/movies/${route.params.id}`)
  data.value = res.data
})
</script>

<template>
  <div v-if="data">
    <h1>{{ data.movie.title }}</h1>

    <ul>
      <li v-for="c in data.characters" :key="c.id">
        <router-link :to="`/characters/${c.id}`">
          {{ c.name }}
        </router-link>
        —
        <router-link :to="`/actors/${c.actor.tmdb_id}`">
          {{ c.actor.name }}
        </router-link>
      </li>
    </ul>

    <router-link :to="`/movies/${route.params.id}/script`">
      View Script
    </router-link>
  </div>

  <div v-else>
    Loading…
  </div>
</template>
