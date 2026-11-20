import { WebSocket, WebSocketServer } from 'ws';
import { telemetrySchema, gatewayBatchSchema } from './validation.js';

function rejectUpgrade(socket, status, message) {
  socket.write(
    `HTTP/1.1 ${status} ${message}\r\nConnection: close\r\nContent-Type: text/plain\r\nContent-Length: ${Buffer.byteLength(message)}\r\n\r\n${message}`,
  );
  socket.destroy();
}

function isAuthorizedGateway(requestUrl, request, gatewayKey) {
  const token =
    request.headers['x-gateway-key'] ||
    request.headers.authorization?.replace(/^Bearer\s+/i, '') ||
    requestUrl.searchParams.get('key');
  return token === gatewayKey;
}

export class RealtimeHub {
  constructor({ server, store, telemetryService, getSnapshot, gatewayKey }) {
    this.store = store;
    this.telemetryService = telemetryService;
    this.getSnapshot = getSnapshot;
    this.gatewayKey = gatewayKey;
    this.browserClients = new Set();
    this.gatewayClients = new Set();
    this.wss = new WebSocketServer({ noServer: true, maxPayload: 64 * 1024, perMessageDeflate: false });

    this.wss.on('connection', (socket, request, kind) => this.handleConnection(socket, request, kind));
    server.on('upgrade', (request, socket, head) => this.handleUpgrade(request, socket, head));

    this.heartbeat = setInterval(() => {
      for (const socket of [...this.browserClients, ...this.gatewayClients]) {
        if (socket.isAlive === false) {
          socket.terminate();
          continue;
        }
        socket.isAlive = false;
        socket.ping();
      }
    }, 30_000);
    this.heartbeat.unref();
  }

  handleUpgrade(request, socket, head) {
    let requestUrl;
    try {
      requestUrl = new URL(request.url, 'http://localhost');
    } catch {
      rejectUpgrade(socket, 400, 'Bad Request');
      return;
    }

    if (requestUrl.pathname === '/ws') {
      this.wss.handleUpgrade(request, socket, head, (ws) => {
        this.wss.emit('connection', ws, request, 'browser');
      });
      return;
    }

    if (requestUrl.pathname === '/ws/gateway') {
      if (!isAuthorizedGateway(requestUrl, request, this.gatewayKey)) {
        rejectUpgrade(socket, 401, 'Unauthorized');
        return;
      }
      this.wss.handleUpgrade(request, socket, head, (ws) => {
        this.wss.emit('connection', ws, request, 'gateway');
      });
      return;
    }

    rejectUpgrade(socket, 404, 'Not Found');
  }

  handleConnection(socket, request, kind) {
    socket.isAlive = true;
    socket.clientKind = kind;
    socket.on('pong', () => {
      socket.isAlive = true;
    });

    if (kind === 'gateway') {
      this.gatewayClients.add(socket);
      this.send(socket, {
        type: 'gateway.ready',
        gatewayId: 'GW-NSK-01',
        protocol: 'sentinel.telemetry.v1',
        serverTime: new Date().toISOString(),
      });
      socket.on('message', (buffer) => this.handleGatewayMessage(socket, buffer));
      socket.on('close', () => this.gatewayClients.delete(socket));
      return;
    }

    this.browserClients.add(socket);
    socket.send(JSON.stringify({ type: 'snapshot', data: this.snapshotPayload() }));
    socket.on('message', (buffer) => {
      try {
        const message = JSON.parse(buffer.toString());
        if (message.type === 'ping') {
          this.send(socket, { type: 'pong', serverTime: new Date().toISOString() });
        }
      } catch {
        // Dashboard clients are read-only; malformed messages are simply ignored.
      }
    });
    socket.on('close', () => this.browserClients.delete(socket));
    socket.on('error', () => this.browserClients.delete(socket));
  }

  handleGatewayMessage(socket, buffer) {
    let payload;
    try {
      payload = JSON.parse(buffer.toString());
    } catch {
      this.send(socket, { type: 'error', message: 'Payload is not valid JSON' });
      return;
    }

    try {
      const result = this.processGatewayPayload(payload);
      this.send(socket, { type: 'ack', ...result, serverTime: new Date().toISOString() });
      this.broadcastSnapshot();
    } catch (error) {
      this.send(socket, { type: 'error', message: error.message });
    }
  }

  processGatewayPayload(payload) {
    const envelope =
      payload?.type === 'telemetry'
        ? { gatewayId: payload.gatewayId, readings: payload.readings }
        : payload;

    if (Array.isArray(envelope?.readings)) {
      const parsed = gatewayBatchSchema.parse(envelope);
      const result = this.telemetryService.ingestBatch(parsed.readings, {
        gatewayId: parsed.gatewayId,
        source: 'gateway-ws',
        firmware: parsed.firmware,
      });
      return { accepted: result.accepted, ignored: result.ignored, nodes: result.results.map((item) => item.nodeId) };
    }

    const reading = telemetrySchema.parse(envelope);
    const result = this.telemetryService.ingest(reading, {
      gatewayId: envelope.gatewayId,
      source: 'gateway-ws',
    });
    return { accepted: result.ignored ? 0 : 1, ignored: result.ignored ? 1 : 0, nodes: [result.nodeId] };
  }

  snapshotPayload() {
    const snapshot = this.getSnapshot();
    snapshot.meta.realtimeClients = this.browserClients.size;
    snapshot.meta.gatewaySockets = this.gatewayClients.size;
    return snapshot;
  }

  send(socket, message) {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  broadcastSnapshot() {
    const payload = JSON.stringify({ type: 'snapshot', data: this.snapshotPayload() });
    for (const socket of this.browserClients) {
      if (socket.readyState === WebSocket.OPEN) socket.send(payload);
    }
  }

  close() {
    clearInterval(this.heartbeat);
    for (const socket of [...this.browserClients, ...this.gatewayClients]) {
      socket.close(1001, 'Server shutting down');
    }
    this.wss.close();
  }
}
