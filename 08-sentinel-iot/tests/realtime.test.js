import assert from 'node:assert/strict';
import http from 'node:http';
import test from 'node:test';
import { WebSocket } from 'ws';
import { createApp } from '../server/app.js';
import { RealtimeHub } from '../server/realtime.js';
import { createStore } from './helpers.js';

const GATEWAY_KEY = 'ws-test-key';

function nextMessage(socket, timeoutMs = 3000) {
  if (socket.messageQueue.length) {
    return Promise.resolve(socket.messageQueue.shift());
  }

  return new Promise((resolve, reject) => {
    const waiter = {
      resolve,
      timer: setTimeout(() => {
        const index = socket.messageWaiters.indexOf(waiter);
        if (index >= 0) socket.messageWaiters.splice(index, 1);
        reject(new Error('Timed out waiting for WebSocket message'));
      }, timeoutMs),
    };
    socket.messageWaiters.push(waiter);
  });
}

function openSocket(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    socket.messageQueue = [];
    socket.messageWaiters = [];
    socket.on('message', (buffer) => {
      let message;
      try {
        message = JSON.parse(buffer.toString());
      } catch {
        return;
      }
      const waiter = socket.messageWaiters.shift();
      if (waiter) {
        clearTimeout(waiter.timer);
        waiter.resolve(message);
      } else {
        socket.messageQueue.push(message);
      }
    });

    const timer = setTimeout(() => {
      socket.terminate();
      reject(new Error(`Timed out opening ${url}`));
    }, 3000);
    socket.once('open', () => {
      clearTimeout(timer);
      socket.on('error', () => {});
      resolve(socket);
    });
    socket.once('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

function expectUpgradeFailure(url, expectedStatus) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      socket.terminate();
      reject(new Error(`Timed out waiting for upgrade failure on ${url}`));
    }, 3000);
    const finish = (callback) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.terminate();
      callback();
    };
    socket.on('unexpected-response', (request, response) => {
      response.resume();
      finish(() => {
        assert.equal(response.statusCode, expectedStatus);
        resolve();
      });
    });
    socket.on('open', () => finish(() => reject(new Error('Expected the upgrade to be rejected'))));
    socket.on('error', (error) => finish(() => reject(error)));
  });
}

async function startServer(store) {
  const app = createApp({
    store,
    simulate: false,
    simulationStatus: () => ({ running: false }),
  });
  const server = http.createServer(app);
  const hub = new RealtimeHub({
    server,
    store,
    telemetryService: app.locals.services.telemetryService,
    getSnapshot: () => app.locals.services.dashboardService.getSnapshot(),
    gatewayKey: GATEWAY_KEY,
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address();

  return {
    port,
    async close() {
      hub.close();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}

test('browser dashboard sockets receive an immediate snapshot and pong replies', async () => {
  const store = createStore({ seed: true });
  const server = await startServer(store);
  const socket = await openSocket(`ws://127.0.0.1:${server.port}/ws`);

  try {
    const snapshotMessage = await nextMessage(socket);
    assert.equal(snapshotMessage.type, 'snapshot');
    assert.equal(snapshotMessage.data.nodes.length, 3);
    assert.equal(snapshotMessage.data.meta.realtimeClients, 1);

    socket.send(JSON.stringify({ type: 'ping' }));
    const pong = await nextMessage(socket);
    assert.equal(pong.type, 'pong');
    assert.ok(pong.serverTime);
  } finally {
    socket.close();
    await server.close();
  }
});

test('gateway sockets require the shared key', async () => {
  const store = createStore({ seed: true });
  const server = await startServer(store);

  try {
    await expectUpgradeFailure(`ws://127.0.0.1:${server.port}/ws/gateway`, 401);
    await expectUpgradeFailure(`ws://127.0.0.1:${server.port}/ws/gateway?key=wrong`, 401);
    await expectUpgradeFailure(`ws://127.0.0.1:${server.port}/ws/unknown`, 404);
  } finally {
    await server.close();
  }
});

test('gateway telemetry is accepted over WebSocket and broadcast to dashboards', async () => {
  const store = createStore();
  const server = await startServer(store);
  const browser = await openSocket(`ws://127.0.0.1:${server.port}/ws`);
  const gateway = await openSocket(
    `ws://127.0.0.1:${server.port}/ws/gateway?key=${GATEWAY_KEY}`,
  );

  try {
    await nextMessage(browser);
    const ready = await nextMessage(gateway);
    assert.equal(ready.type, 'gateway.ready');

    gateway.send(
      JSON.stringify({
        type: 'telemetry',
        gatewayId: 'GW-NSK-01',
        firmware: 'sentinel-gw 1.4.2',
        readings: [
          {
            nodeId: 'SN-NASH-01',
            lat: 19.9975,
            lon: 73.7898,
            temp: 29.1,
            humidity: 93,
            rain: 27,
            waterLevel: 136,
            vibration: 12,
            aqi: 86,
            sos: false,
            battery: 3.8,
            rssi: -69,
            snr: 7.1,
            timestamp: new Date().toISOString(),
          },
        ],
      }),
    );

    const ack = await nextMessage(gateway);
    assert.equal(ack.type, 'ack');
    assert.equal(ack.accepted, 1);
    assert.equal(ack.ignored, 0);
    assert.deepEqual(ack.nodes, ['SN-NASH-01']);

    const broadcast = await nextMessage(browser);
    assert.equal(broadcast.type, 'snapshot');
    const node = broadcast.data.nodes.find((item) => item.id === 'SN-NASH-01');
    assert.equal(node.latest.waterLevel, 136);
    assert.equal(node.risk.level, 'severe');
    assert.equal(store.getNode('SN-NASH-01').latest.waterLevel, 136);
  } finally {
    browser.close();
    gateway.close();
    await server.close();
  }
});

test('malformed gateway frames return an error without closing the socket', async () => {
  const store = createStore();
  const server = await startServer(store);
  const gateway = await openSocket(
    `ws://127.0.0.1:${server.port}/ws/gateway?key=${GATEWAY_KEY}`,
  );

  try {
    await nextMessage(gateway);

    gateway.send('{not-json');
    const error = await nextMessage(gateway);
    assert.equal(error.type, 'error');
    assert.match(error.message, /valid JSON/);

    gateway.send(JSON.stringify({ nodeId: 'SN-NASH-01' }));
    const validationError = await nextMessage(gateway);
    assert.equal(validationError.type, 'error');
    assert.match(validationError.message, /Invalid input|invalid/i);
  } finally {
    gateway.close();
    await server.close();
  }
});
