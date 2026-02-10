<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()

const data = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const res = await api.get(`/actors/${route.params.id}`)
    data.value = res.data
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = "Actor not found"
    } else {
      error.value = "Something went wrong"
    }
  }
})
</script>

<template>
  <div class="appearances">
    <section v-if="data">
      <header class="actor-header">
        <div>{{ data.actor.name }}</div>
      </header>

      <div class="appearances-table">
        <div class="appearance-header">
          <span>Movie</span>
          <span>Character</span>
        </div>

        <div
          v-for="m in data.movies"
          :key="m.tmdb_id"
          class="appearance-row"
        >
          <router-link :to="`/movies/${m.tmdb_id}`">
            {{ m.title }} ({{ m.year }})
          </router-link>

          <router-link :to="`/characters/${m.character.id}`">
            {{ m.character.name }}
          </router-link>
        </div>
      </div>
    </section>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else class="loading">
      Loading filmography…
    </div>
  </div>
</template>

<style scoped>
  a {
    color: blue;
    text-decoration: none;
  }

  .appearances {
    padding: 10px;
  }

  .actor-header {
    font-size: 25px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 1rem;
  }

  .appearances-table {
    display: grid;
    gap: 0.25rem;
  }

  .appearance-header,
  .appearance-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .appearance-header {
    font-weight: 600;
    border-bottom: 2px solid #ddd;
    padding-bottom: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .appearance-row {
    padding: 0.4rem 0;
  }

  .appearance-row a {
    display: inline-block;
    width: fit-content;
  }
</style>
