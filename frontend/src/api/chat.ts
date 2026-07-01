import { apiFetch } from "./client";
import type { ChatRequest, ChatResponse, HealthResponse } from "./types";

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export function postChat(request: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
