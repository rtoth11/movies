<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const data = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const res = await api.get(`/movies/${route.params.id}`)
    data.value = res.data
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = "Movie not found"
    } else {
      error.value = "Something went wrong"
    }
  }
})
</script>

<template>
  <div class="movie-details">
    <section v-if="data">
      <header class="movie-header">
        <div>{{ data.movie.title }}</div>
      </header>

      <div>
        <router-link
          id="view-script-link"
          :to="`/movies/${data.movie.tmdb_id}/script`"
        >
          View script
        </router-link>
      </div>

      <div class="cast-table">
        <div class="cast-header">
          <span>Character</span>
          <span>Actor</span>
        </div>

        <div
          v-for="c in data.characters"
          :key="c.id"
          class="cast-row"
        >
          <router-link :to="`/characters/${c.id}`">
            {{ c.name }}
          </router-link>

          <router-link :to="`/actors/${c.actor.tmdb_id}`">
            {{ c.actor.name }}
          </router-link>
        </div>
      </div>
    </section>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else class="loading">
      Loading movie details…
    </div>
  </div>
</template>

<style scoped>
  a {
    color: blue;
    text-decoration: none;
  }

  .movie-details {
    padding: 10px;
  }

  .movie-header {
    font-size: 25px;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 1rem;
  }

  #view-script-link {
    display: inline-block;
    margin-bottom: 1.5rem;
  }

  .cast-table {
    display: grid;
    gap: 0.25rem;
  }

  .cast-header,
  .cast-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .cast-header {
    font-weight: 600;
    border-bottom: 2px solid #ddd;
    padding-bottom: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .cast-row {
    padding: 0.4rem 0;
  }

  .cast-row a {
    display: inline-block;
    width: fit-content;
  }
</style>
