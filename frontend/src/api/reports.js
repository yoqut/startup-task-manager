import client from "./client";

export const reportsApi = {
  list:        (params)     => client.get("/reports/reports/", { params }),
  get:         (id)         => client.get(`/reports/reports/${id}/`),
  create:      (data)       => client.post("/reports/reports/", data),
  update:      (id, data)   => client.patch(`/reports/reports/${id}/`, data),
  addComment:  (id, data)   => client.post(`/reports/reports/${id}/comments/`, data),
  acknowledge: (id)         => client.post(`/reports/reports/${id}/acknowledge/`),
};
