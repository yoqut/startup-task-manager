import client from "./client";

export const integrationsApi = {
  list:          ()       => client.get("/integrations/crm/"),
  get:           (id)     => client.get(`/integrations/crm/${id}/`),
  create:        (data)   => client.post("/integrations/crm/", data),
  update:        (id, d)  => client.patch(`/integrations/crm/${id}/`, d),
  delete:        (id)     => client.delete(`/integrations/crm/${id}/`),
  logs:          (id)     => client.get(`/integrations/crm/${id}/logs/`),
  testConnection:(id)     => client.post(`/integrations/crm/${id}/test/`),
  manualSync:    (id)     => client.post(`/integrations/crm/${id}/sync/`),
};
