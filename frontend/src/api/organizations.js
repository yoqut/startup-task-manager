import client from "./client";

export const organizationsApi = {
  // Departments CRUD
  list:   ()           => client.get("/organizations/departments/"),
  get:    (id)         => client.get(`/organizations/departments/${id}/`),
  create: (data)       => client.post("/organizations/departments/", data),
  update: (id, data)   => client.patch(`/organizations/departments/${id}/`, data),
  remove: (id)         => client.delete(`/organizations/departments/${id}/`),

  // Members
  getMembers:    (id)       => client.get(`/organizations/departments/${id}/members/`),
  assignMembers: (id, data) => client.post(`/organizations/departments/${id}/assign-members/`, data),
  removeMember:  (id, data) => client.post(`/organizations/departments/${id}/remove-member/`, data),

  // Head
  setHead: (id, data) => client.post(`/organizations/departments/${id}/set-head/`, data),
};
