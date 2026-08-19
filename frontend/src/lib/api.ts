const API_BASE = "/api";

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  source: string;
  posted_at: string | null;
  score: number;
  label: "close" | "good" | "weak";
  saved: boolean;
  applied: boolean;
  notes: string;
}

export interface DashboardStats {
  close_matches: number;
  good_matches: number;
  weak_matches: number;
  total_jobs: number;
  saved_count: number;
  applied_count: number;
  has_resume: boolean;
}

export interface Resume {
  file_name: string;
  skills: string[];
  titles: string[];
  years_experience: number;
  uploaded_at: string;
}

export interface SearchProfile {
  country: string;
  location: string;
  locations: { city: string; country: string }[];
  extra_keywords: string;
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d))).join(", ");
  }
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    if (!path.includes("/auth/login")) {
      window.location.href = "/login";
    }
    throw new Error("Invalid email or password");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 404 || res.status === 502 || res.status === 503) {
      throw new Error("Server is waking up — wait 30 seconds and try again");
    }
    throw new Error(formatErrorDetail(err.detail, res.statusText || "Request failed"));
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export async function waitForServer(maxAttempts = 12, delayMs = 5000): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) return;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error("Server is still starting — please wait a moment and refresh");
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me"),

  users: () => request<User[]>("/users"),

  dashboard: () => request<DashboardStats>("/dashboard"),

  jobs: (params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return request<Job[]>(`/jobs?${qs}`);
  },

  refreshJobs: () =>
    request<{ jobs_fetched: number; matches_updated: number }>("/jobs/refresh", {
      method: "POST",
      signal: AbortSignal.timeout(120000),
    }),

  updateJobStatus: (jobId: number, data: { saved?: boolean; applied?: boolean; notes?: string }) =>
    request(`/jobs/${jobId}/status`, { method: "PATCH", body: JSON.stringify(data) }),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("/resumes/upload", { method: "POST", body: form });
  },

  getResume: () => request<Resume | null>("/resumes/me"),

  getProfile: () => request<SearchProfile>("/profile"),

  updateProfile: (data: Partial<SearchProfile>) =>
    request<SearchProfile>("/profile", { method: "PUT", body: JSON.stringify(data) }),
};
