<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()

const movieTitle = ref("")
const script = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const scriptRes = await api.get(`/movies/${route.params.id}/script`)
    script.value = scriptRes.data.blocks
    movieTitle.value = scriptRes.data.movie_title
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
  <div class="page" v-if="script">
    <header class="page-header">
      <h1 class="movie-title">
        {{ movieTitle }}
      </h1>
    </header>
    <div class="script">
      <div
        v-for="b in script"
        :key="b.index_in_script"
        class="script-block"
        :class="b.type"
        :id="'line-' + b.index_in_script"
      >
        <template v-if="b.type === 'scene'">
          {{ b.text }}
        </template>

        <template v-else-if="b.type === 'description'">
          {{ b.text }}
        </template>

        <template v-else-if="b.type === 'dialogue'">
          <div class="character">
            {{ b.character }}
            <span v-if="b.suffix" class="suffix">({{ b.suffix }})</span>
          </div>

          <div v-if="b.parenthetical" class="parenthetical">
            ({{ b.parenthetical }})
          </div>

          <div class="dialogue">
            {{ b.text || "DIALOGUE MISSING" }}
          </div>
        </template>
      </div>
    </div>
  </div>

  <div v-else-if="error" class="error">
    {{ error }}
  </div>

  <div v-else class="loading">
    Loading movie script…
  </div>
</template>

<style scoped>
.page {
  width: 685px;
  padding: 16px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
  text-align: center;
}

.movie-title {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #333;
}

.script {
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  font-size: 14px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.script-block {
  margin-bottom: 10px;
  white-space: pre-wrap;
}

.scene {
  margin-top: 20px;
  margin-left: 8ch;
  font-weight: bold;
  text-transform: uppercase;
  text-decoration: underline;
}

.description {
  margin-left: 8ch;
  max-width: 70ch;
}

.character {
  margin-left: 18ch;
  font-weight: bold;
}

.suffix {
  font-weight: normal;
  margin-left: 4px;
}

.parenthetical {
  margin-left: 24ch;
  font-style: italic;
  max-width: 30ch;
}

.script-block.dialogue{
  margin-left: 20ch;
  max-width: 48ch;
}

.dialogue {
  margin-left: 2ch;
}
</style>
