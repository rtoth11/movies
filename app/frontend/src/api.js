import axios from "axios"

const api = axios.create({
  baseURL: "/api", // http://localhost:5000/api or /api (ECS)
})

export default api
