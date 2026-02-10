<script setup>
import { ref, onMounted, computed } from "vue"
import { useRoute } from "vue-router"
import api from "../api"

const route = useRoute()
const data = ref(null)
const script = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const charRes = await api.get(`/characters/${route.params.id}`)
    data.value = charRes.data

    const movieId = data.value.character.movie.tmdb_id
    const scriptRes = await api.get(`/movies/${movieId}/script`)
    script.value = scriptRes.data.blocks
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = "Character not found"
    } else {
      error.value = "Something went wrong"
    }
  }
})

const page = ref(1)
const pageSize = 12

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

const pagedDialogues = computed(() => {
  if (!data.value?.dialogues) return []
  const start = (page.value - 1) * pageSize
  return data.value.dialogues.slice(start, start + pageSize)
})

const totalPages = computed(() => {
  if (!data.value?.dialogues) return 1
  return pageRange(page.value, Math.ceil(data.value.dialogues.length / pageSize))
})

const selectedIndex = ref(null)

function jumpToLine(index) {
  selectedIndex.value = index
  const el = document.getElementById(`line-${index}`)
  if (el) {
    el.scrollIntoView({
      behavior: "smooth",
      block: "center"
    })
  }
}
</script>

<template>
  <div class="page" v-if="data && script">
    <div class="left">
      <div class="left-content">
        <div>
          <div class="character-name">
            {{ data.character.name }}
          </div>
          <div class="movie-title">
            Movie:
            <router-link :to="`/movies/${data.character.movie.tmdb_id}`">
              {{ data.character.movie.title }}
            </router-link>
          </div>
        </div>

        <div class="dialogues-title">Dialogues</div>
        <ul class="dialogue-list">
          <li
            v-for="d in pagedDialogues"
            :key="d.index"
            class="dialogue-item"
            :class="{ active: d.index === selectedIndex }"
            @click="jumpToLine(d.index)"
          >
            <span class="line-number">#{{ d.index }}</span>
            {{ d.dialogue }}
          </li>
        </ul>

        <div class="pagination">
          <button
            v-for="p in totalPages"
            :key="p"
            :disabled="p === '…'"
            :class="{ active: p === page }"
            @click="p !== '…' && (page = p)"
          >
            {{ p }}
          </button>
        </div>
      </div>
    </div>

    <div class="right">
      <div
        v-for="b in script"
        :key="b.index_in_script"
        class="script-block"
        :class="[
          b.type,
          { active: b.index_in_script === selectedIndex }
        ]"
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
    Loading character details…
  </div>
</template>

<style scoped>
a {
  color: blue;
  text-decoration: none;
}

.page {
  display: grid;
  grid-template-columns: 600px 685px;
  gap: 20px;
  padding: 16px;
  background: #f7f8fa;
  height: calc(100vh - 100px);
}

.left,
.right {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.left-content {
  padding: 16px;
}

.character-name{
  font-size: 25px;
  font-weight: bold;
  text-transform : lowercase;
  display: inline-block;
}

.character-name:first-letter{
  text-transform : uppercase;
}

.movie-title {
  margin-top: 8px;
  font-size: 16px;
  color: #555;
  display: inline-block;
  float: right;
}

.dialogues-title {
  margin-top: 24px;
  margin-bottom: 12px;
  font-size: 18px;
  border-bottom: 2px solid #4a90e2;
  padding-bottom: 4px;
}

.dialogue-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.dialogue-item {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: background 0.15s ease, transform 0.1s ease;
}

.dialogue-item:hover {
  cursor: pointer;
  background: #f0f0f0;
  transform: translateX(2px);
}

.dialogue-item.active {
  background: #e9f2ff;
  border-left: 4px solid #4a90e2;
}

.line-number {
  font-size: 12px;
  color: #999;
  margin-right: 6px;
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

.right {
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  font-size: 14px;
}

.script-block {
  margin-bottom: 10px;
  white-space: pre-wrap;
}

.script-block.active {
  background: #fff3cd;
  outline: none;
  box-shadow: inset 4px 0 0 #f0c36d;
  border-radius: 6px;
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
