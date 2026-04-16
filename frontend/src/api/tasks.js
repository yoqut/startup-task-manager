import client from "./client";

export const tasksApi = {
  list: (params) => client.get("/tasks/tasks/", { params }),
  get: (id) => client.get(`/tasks/tasks/${id}/`),
  create: (data) => client.post("/tasks/tasks/", data),
  update: (id, data) => client.patch(`/tasks/tasks/${id}/`, data),
  delete: (id) => client.delete(`/tasks/tasks/${id}/`),
  myTasks: () => client.get("/tasks/tasks/my-tasks/"),
  overdue: () => client.get("/tasks/tasks/overdue/"),
  blocked: () => client.get("/tasks/tasks/blocked/"),
  getComments:  (id)       => client.get(`/tasks/tasks/${id}/comments/`),
  addComment:   (id, data) => client.post(`/tasks/tasks/${id}/comments/`, data),
  sendReport:   (id, data) => client.post(`/tasks/tasks/${id}/report/`, data),
  workflows: () => client.get("/tasks/workflows/"),
  createWorkflow: (data) => client.post("/tasks/workflows/", data),
};
