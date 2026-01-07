<script setup>
import { ref } from "vue"
import api from "../api"

const q = ref("")
const movies = ref([])
const types = ref({
  dialogue: true,
  description: true,
  scene: true,
  unknown: false,
})

const search = async () => {
  const enabledTypes = Object.keys(types.value)
    .filter(k => types.value[k])

  const res = await api.get("/movies", {
    params: {
      q: q.value,
      types: enabledTypes
    }
  })

  movies.value = res.data
}
</script>

<template>
  <div>
    <h1>Movie Search</h1>

    <input v-model="q" placeholder="Search movies…" />

    <div>
      <label v-for="(v, k) in types" :key="k">
        <input type="checkbox" v-model="types[k]" />
        {{ k }}
      </label>
    </div>

    <button @click="search">Search</button>

    <ul>
      <li v-for="m in movies" :key="m.tmdb_id">
        <router-link :to="`/movies/${m.tmdb_id}`">
          {{ m.title }} ({{ m.year }})
        </router-link>
        {{ m.content }}
        <div v-if="m.character_id">
          <router-link :to="`/characters/${m.character_id}`">
            ({{ m.character }})
          </router-link>
        </div>
      </li>
    </ul>
  </div>
</template>
