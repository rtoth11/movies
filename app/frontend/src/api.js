import axios from "axios"

const api = axios.create({
  baseURL: "http://localhost:5000/api", // http://localhost:5000/api or /api (ECS)
})

export default api
