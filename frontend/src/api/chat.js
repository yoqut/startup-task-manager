import client from "./client";

export const chatApi = {
  listRooms:   ()     => client.get("/chat/rooms/"),
  getRoom:     (id)   => client.get(`/chat/rooms/${id}/`),
  createRoom:  (data) => client.post("/chat/rooms/", data),
  updateRoom:  (id, data) => client.patch(`/chat/rooms/${id}/`, data),
  deleteRoom:  (id)   => client.delete(`/chat/rooms/${id}/`),
  getMessages: (id)   => client.get(`/chat/rooms/${id}/messages/`),
};
