<script setup>
import { ref, computed, watch } from "vue"
import api from "../api"

const q = ref("")
const selectedMovie = ref(null)
const hasSearched = ref(false)
const isLoadingMovies = ref(false)
const searchedQuery = ref("")
const searchError = ref(null)
const blocksError = ref(null)

const types = ref({
  description: false,
  dialogue: false,
  scene: false,
  unknown: false,
})

const movies = ref([])
const moviesTotal = ref(0)
const moviesPage = ref(1)
const MOVIES_LIMIT = 20

const blocks = ref([])
const blocksTotal = ref(0)
const blocksPage = ref(1)
const BLOCKS_LIMIT = 10

const enabledTypes = computed(() =>
  Object.keys(types.value).filter(k => types.value[k])
)

const gotResults = computed(() => moviesTotal.value > 0)

const moviesPageCount = computed(() =>
  Math.ceil(moviesTotal.value / MOVIES_LIMIT)
)

const blocksPageCount = computed(() =>
  Math.ceil(blocksTotal.value / BLOCKS_LIMIT)
)

const fetchMovies = async () => {
  selectedMovie.value = null
  isLoadingMovies.value = true

  try {
    const res = await api.get("/movies", {
      params: {
        q: q.value,
        types: enabledTypes.value,
        page: moviesPage.value,
        limit: MOVIES_LIMIT
      }
    })

    movies.value = res.data.items
    moviesTotal.value = res.data.total
  } catch (err) {
    searchError.value = "Failed to fetch movies"
  } finally {
    isLoadingMovies.value = false
  }
}

const search = () => {
  hasSearched.value = true
  searchError.value = null
  searchedQuery.value = q.value
  selectedMovie.value = null
  blocks.value = []
  blocksTotal.value = 0
  blocksPage.value = 1
  moviesPage.value = 1
  fetchMovies()
}

let blocksRequestId = 0

const fetchBlocks = async () => {
  if (!selectedMovie.value) return

  const requestId = ++blocksRequestId
  blocksError.value = null

  try {
    const res = await api.get(
      `/movies/${selectedMovie.value.tmdb_id}/script_blocks`,
      {
        params: {
          q: q.value,
          types: enabledTypes.value,
          page: blocksPage.value,
          limit: BLOCKS_LIMIT
        }
      }
    )

    if (requestId !== blocksRequestId) return

    blocks.value = res.data.items
    blocksTotal.value = res.data.total
  } catch (err) {
    if (requestId !== blocksRequestId) return
    blocksError.value = "Failed to fetch script blocks"
  }
}

const openMovie = (movie) => {
  selectedMovie.value = movie
  blocks.value = []
  blocksPage.value = 1
  blocksTotal.value = 0
  fetchBlocks()
}

const closeDrawer = () => {
  selectedMovie.value = null
  blocks.value = []
}

const goToMoviePage = (p) => {
  moviesPage.value = p
  fetchMovies()
}

watch(blocksPage, fetchBlocks)

const highlight = (text) => {
  if (!q.value) return text
  const re = new RegExp(`(${q.value.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')})`, "gi")
  return text.replace(re, "<mark>$1</mark>")
}

const pageRange = (current, total, delta = 2) => {
  const pages = []
  const start = Math.max(1, current - delta)
  const end = Math.min(total, current + delta)

  if (start > 1) {
    pages.push(1)
    if (start > 2) pages.push("…")
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (end < total) {
    if (end < total - 1) pages.push("…")
    pages.push(total)
  }

  return pages
}

const moviePages = computed(() =>
  pageRange(moviesPage.value, moviesPageCount.value)
)

const blockPages = computed(() =>
  pageRange(blocksPage.value, blocksPageCount.value)
)
</script>

<template>
  <div class="page" :class="{ 'got-results': gotResults }">
    <div v-if="searchError">
      {{ searchError }}
    </div>
    <div v-else-if="hasSearched && !isLoadingMovies && !movies.length">
      No movies found for "{{ searchedQuery }}."
    </div>
    <div class="search-panel">
      <h1>Movie search</h1>

      <div class="search-row">
        <input
          type="text"
          placeholder="Search movies…"
          v-model="q"
          @keyup.enter="search"
          :disabled="isLoadingMovies"
        />
        <button @click="search">Search</button>
      </div>

      <div class="search-types">
        <strong>Search in:</strong>
        <label v-for="(v, k) in types" :key="k">
          <input type="checkbox" v-model="types[k]" />
          {{ k }}
        </label>
      </div>
    </div>

    <div class="content">
      <table class="movie-table" v-if="movies.length">
        <thead>
          <tr>
            <th class="col-title-header">Title</th>
            <th class="col-year-header">Year</th>
            <th class="col-matches-header">Matches</th>
            <th class="col-link-header"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="movie in movies"
            :key="movie.tmdb_id"
            :class="{ selected: selectedMovie?.tmdb_id === movie.tmdb_id }"
          >
            <td
              class="col-title"
              @click="openMovie(movie)"
            >
              {{ movie.title }}
            </td>
            <td class="col-year">{{ movie.year }}</td>
            <td class="col-matches">{{ movie.total_matches }}</td>
            <td class="col-link">
              <router-link :to="`/movies/${movie.tmdb_id}`" @click.stop>
                Details
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button
          v-for="p in moviePages"
          :key="p"
          :disabled="p === '…'"
          :class="{ active: p === moviesPage }"
          @click="p !== '…' && goToMoviePage(p)"
        >
          {{ p }}
        </button>
      </div>
    </div>

    <aside
      class="drawer"
      :key="selectedMovie?.tmdb_id"
      :class="{ open: selectedMovie }"
    >
      <div class="drawer-header">
        <h2>
          {{ selectedMovie?.title }}
          <span>({{ selectedMovie?.year }})</span>
        </h2>
        <button class="close-btn" @click="closeDrawer">✕</button>
      </div>

      <div v-if="blocksError">
        {{ blocksError }}
      </div>
      <div v-else>
        <ul class="results-list">
          <li
            v-for="r in blocks"
            class="result-item"
            :class="`type-${r.type}`"
          >
            <div class="result-type">
              {{ r.type }}
            </div>
            <div class="result-meta" v-if="r.character_id">
              <router-link :to="`/characters/${r.character_id}`">
                {{ r.character }}
              </router-link>
            </div>

            <div
              class="result-content"
              v-html="highlight(r.content)"
            />
          </li>
        </ul>

        <div
          class="pagination"
          :key="selectedMovie?.tmdb_id"
        >
          <button
            v-for="p in blockPages"
            :key="p"
            :disabled="p === '…'"
            :class="{ active: p === blocksPage }"
            @click="p !== '…' && (blocksPage = p)"
          >
            {{ p }}
          </button>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
a {
  color: blue;
  text-decoration: none;
}

.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page.got-results {
  display: grid;
  grid-template-columns: 265px minmax(0, 1fr) 800px;
  gap: 16px;
  align-items: start;
}

.search-panel {
  max-width: 600px;
  margin: 0 auto 24px;
  transition: all 0.3s ease;
  height: 100%;
}

.page.got-results .search-panel {
  width: 265px;
  max-width: none;
  margin: 0;
  flex-shrink: 0;
  position: sticky;
  top: 16px;
}

.page.got-results .search-panel h1 {
  font-size: 1.25rem;
  margin-bottom: 12px;
}

.search-row {
  display: flex;
  gap: 8px;
}

input[type="text"] {
  flex: 1;
  padding: 6px;
}

.search-types {
  margin-top: 8px;
  font-size: 0.9em;
}

.search-types label {
  margin-right: 12px;
}

.movie-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 0;
}

.movie-table th,
.movie-table td {
  padding: 8px;
  border-bottom: 1px solid #ddd;
}

.movie-table tr:hover {
  background: #f5f5f5;
}

.movie-table tr.selected {
  background: #e8f0ff;
}

.col-title {
  cursor: pointer;
}

.col-year-header,
.col-matches-header,
.col-link-header,
.col-year,
.col-matches,
.col-link {
  text-align: center;
  white-space: nowrap;
}

.col-year {
  width: 72px;
}

.col-matches {
  width: 96px;
}

.col-link {
  width: 80px;
}

.pagination {
  display: flex;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
  padding: 8px;
  justify-content: center;
}

.pagination button {
  padding: 4px 8px;
  border-radius: 999px;
  border: none;
  background: #f0f0f0;
  cursor: pointer;
  width: 32px;
  height: 32px;
}

.pagination button.active {
  background: #4a90e2;
  color: white;
  border-color: #4a90e2;
}

.pagination button:disabled {
  cursor: default;
  opacity: 0.6;
}

.pagination button:hover:not(:disabled) {
  background: #e0e0e0;
}

.drawer {
  opacity: 0;
  transform: translateX(16px);
  pointer-events: none;
  transition: all 0.25s ease;
}

.drawer.open {
  opacity: 1;
  transform: translateX(0);
  pointer-events: auto;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
}

.results-list {
  list-style: none;
  padding: 0;
  margin-top: 16px;
}

.result-item {
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 3px solid #ccc;
}

.type-dialogue {
  border-color: #4a90e2;
}

.type-description {
  border-color: #7b8a8b;
}

.type-scene {
  border-color: #27ae60;
}

.type-unknown {
  border-color: #aaa;
}

.result-type {
  display: inline-block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #afafaf;
}

.type-dialogue .result-type {
  background: #e8f0ff; color: #2c5aa0;
}

.type-scene .result-type {
  background: #e8f8ef;
  color: #1e8449;
}

.type-description .result-type {
  background: #f2f3f4;
}

.result-meta {
  font-size: 0.85em;
  margin-bottom: 4px;
}

.result-meta a {
  text-decoration: underline;
  font-size: 1.1em;
}

mark {
  background: #ffe58a;
  padding: 0 2px;
}
</style>
