import { delay, http, HttpResponse } from "msw";
import type { HealthResponse } from "../api/types";
import { getMockResponse } from "./data";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8080";

export const handlers = [
  http.get(`${API_BASE_URL}/health`, () => {
    return HttpResponse.json<HealthResponse>({ status: "ok" });
  }),

  http.post(`${API_BASE_URL}/chat`, async ({ request }) => {
    const body = (await request.json()) as { message?: string };
    const message = body.message ?? "";

    await delay(800);

    return HttpResponse.json(getMockResponse(message));
  }),
];
