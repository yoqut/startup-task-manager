import client from "./client";

export const authApi = {
  register: (data) => client.post("/auth/register/", data),
  login: (data) => client.post("/auth/login/", data),
  logout: (data) => client.post("/auth/logout/", data),
  me: () => client.get("/auth/me/"),
  updateMe: (data) => client.patch("/auth/me/", data),
  team: () => client.get("/auth/team/"),
  inviteMember: (data) => client.post("/auth/team/invite/", data),
  acceptInvite: (data) => client.post("/auth/team/accept-invite/", data),
};
