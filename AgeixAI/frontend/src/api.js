import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API]', err.response?.status, err.config?.url, err.message);
    return Promise.reject(err);
  }
);

// ── WebSocket ──────────────────────────────────────────────────────────────

export class DashboardWebSocket {
  constructor(onMessage, onStatusChange) {
    this.onMessage = onMessage;
    this.onStatusChange = onStatusChange;
    this.ws = null;
    this.attempts = 0;
    this.maxAttempts = 10;
    this.interval = 2000;
    this._intentional = false;
    this._queue = [];
    this.connect();
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket('ws://localhost:8000/ws/dashboard');
    this.ws.onopen = () => {
      this.attempts = 0;
      this.onStatusChange?.(true);
      while (this._queue.length) this.ws.send(JSON.stringify(this._queue.shift()));
    };
    this.ws.onmessage = (e) => {
      try {
        this.onMessage?.(JSON.parse(e.data));
      } catch { /* ignore parse errors */ }
    };
    this.ws.onclose = () => {
      this.onStatusChange?.(false);
      if (!this._intentional) this._reconnect();
    };
    this.ws.onerror = () => {};
  }

  _reconnect() {
    if (this.attempts >= this.maxAttempts) return;
    this.attempts++;
    const delay = this.interval * Math.min(this.attempts, 5);
    setTimeout(() => this.connect(), delay);
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(data));
    else this._queue.push(data);
  }

  close() {
    this._intentional = true;
    this.ws?.close(1000);
  }
}

// ── API Methods ──────────────────────────────────────────────────────────

export const labApi = {
  getStatus: () => api.get('/api/lab/status'),
  launchAttack: (attackType, target) => api.post('/api/lab/launch-attack', { attack_type: attackType, target }),
  checkNetwork: () => api.post('/api/lab/check-network'),
};

export const decisionApi = {
  submit: (decisionId, action, metadata = {}) =>
    api.post('/api/human-decision', { decision_id: decisionId, action, metadata }),
};

export const dashboardApi = {
  getHealth: () => api.get('/api/health'),
};

export default api;
