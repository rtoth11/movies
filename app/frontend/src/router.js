import { createRouter, createWebHistory } from "vue-router"
import MovieSearch from "./pages/MovieSearch.vue"
import MovieDetails from "./pages/MovieDetails.vue"
import ActorDetails from "./pages/ActorDetails.vue"
import CharacterDetails from "./pages/CharacterDetails.vue"
import MovieScript from "./pages/MovieScript.vue"

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: MovieSearch },
    { path: "/movies/:id", component: MovieDetails },
    { path: "/actors/:id", component: ActorDetails },
    { path: "/characters/:id", component: CharacterDetails },
    { path: "/movies/:id/script", component: MovieScript }
  ]
})
