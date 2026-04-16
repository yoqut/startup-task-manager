import client from "./client";

export const agentsApi = {
  configs:        ()          => client.get("/agents/configs/"),
  updateConfig:   (id, data)  => client.patch(`/agents/configs/${id}/`, data),
  triggerAgent:   (id, data)  => client.post(`/agents/configs/${id}/trigger/`, data),
  logs:           (params)    => client.get("/agents/logs/", { params }),
  getLog:         (id)        => client.get(`/agents/logs/${id}/`),
};

export const approvalsApi = {
  list: (params) => client.get("/approvals/", { params }),
  pending: () => client.get("/approvals/pending/"),
  approve: (id, data) => client.post(`/approvals/${id}/approve/`, data),
  reject: (id, data) => client.post(`/approvals/${id}/reject/`, data),
};
