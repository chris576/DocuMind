export interface GatewayRequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
}

/**
 * Thin HTTP client for the DocuMind gateway. The gateway is reachable over a
 * private REST API; MCP itself is only spoken locally between the agent and
 * this server over stdio.
 */
export class GatewayClient {
  private readonly baseUrl: string;
  private readonly token: string | undefined;

  constructor() {
    this.baseUrl = (process.env.GATEWAY_URL ?? 'http://localhost:3001').replace(
      /\/$/,
      '',
    );
    this.token = process.env.GATEWAY_API_TOKEN;
  }

  async request(path: string, options: GatewayRequestOptions = {}): Promise<unknown> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });

    const contentType = response.headers.get('content-type') ?? '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      throw new Error(
        `Gateway error ${response.status}: ${JSON.stringify(payload)}`,
      );
    }

    return payload;
  }
}
