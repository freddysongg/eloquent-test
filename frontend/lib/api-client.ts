/**
 * API Client for EloquentAI backend communication
 *
 * Provides typed API client with authentication, error handling,
 * and request/response interceptors.
 */

// Server-side import removed from client-side code

interface ApiClientConfig {
  baseURL?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

interface ApiResponse<T = unknown> {
  data: T;
  status: number;
  statusText: string;
  headers: Headers;
}

interface ApiError extends Error {
  status?: number;
  statusText?: string;
  data?: unknown;
}

class ApiClient {
  private baseURL: string;
  private timeout: number;
  private defaultHeaders: Record<string, string>;

  constructor(config: ApiClientConfig = {}) {
    this.baseURL =
      config.baseURL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "http://localhost:8000";
    this.timeout = config.timeout || 30000;
    this.defaultHeaders = {
      "Content-Type": "application/json",
      ...config.headers,
    };
  }

  private async request<T = unknown>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}/api/v1${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.defaultHeaders,
          ...options.headers,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.text().catch(() => null);
        const error: ApiError = new Error(
          `API request failed: ${response.status} ${response.statusText}`,
        );
        error.status = response.status;
        error.statusText = response.statusText;
        error.data = errorData;
        throw error;
      }

      const data = await response.json().catch(() => null);

      return {
        data,
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === "AbortError") {
        const timeoutError: ApiError = new Error("Request timeout");
        timeoutError.status = 408;
        throw timeoutError;
      }

      throw error;
    }
  }

  async get<T = unknown>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: "GET",
    });
  }

  async post<T = unknown>(
    endpoint: string,
    data?: unknown,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : null,
    });
  }

  async put<T = unknown>(
    endpoint: string,
    data?: unknown,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : null,
    });
  }

  async patch<T = unknown>(
    endpoint: string,
    data?: unknown,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : null,
    });
  }

  async delete<T = unknown>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: "DELETE",
    });
  }
}

// Default API client instance
export const apiClient = new ApiClient();

// Helper for creating authenticated requests
export async function createAuthenticatedClient(
  token: string,
): Promise<ApiClient> {
  return new ApiClient({
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

// Note: Server-side API client functionality moved to server-side utilities
// Use the client-side useApiClient hook for authenticated requests from components
