<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const data = ref(null)

onMounted(async () => {
  const res = await api.get(`/characters/${route.params.id}`)
  data.value = res.data
})
</script>

<template>
  <div v-if="data">
    <h1>{{ data.character.name }}</h1>

    <p>
      Movie:
      <router-link :to="`/movies/${data.character.movie.tmdb_id}`">
        {{ data.character.movie.title }}
      </router-link>
    </p>

    <h2>Dialogues</h2>
    <ul>
      <li v-for="d in data.dialogues" :key="d.index">
        {{ d.dialogue }}
      </li>
    </ul>
  </div>
</template>
