import config from './config.js';
import { SITE } from './site.js';
import { createId, nowIso } from './utils.js';

export class CommandError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'CommandError';
    this.status = status;
  }
}

function operatorName(value) {
  return value?.trim() || config.operatorName;
}

export class CommandService {
  constructor(store) {
    this.store = store;
  }

  acknowledgeAlert(alertId, operator) {
    const existing = this.store.getAlert(alertId);
    if (!existing) throw new CommandError('Alert not found', 404);
    if (existing.status !== 'active') {
      throw new CommandError(`Alert is already ${existing.status}`, 409);
    }

    const alert = this.store.acknowledgeAlert(alertId, operatorName(operator));
    this.store.addIncident({
      nodeId: alert.nodeId,
      nodeName: alert.nodeName,
      type: 'acknowledgement',
      severity: alert.severity,
      title: `Alert acknowledged — ${alert.nodeName ?? 'regional alert'}`,
      detail: `${operatorName(operator)} acknowledged "${alert.title}".`,
      source: 'operator',
      status: 'acknowledged',
      metadata: { alertId: alert.id, operator: operatorName(operator) },
    });
    return alert;
  }

  acknowledgeAll(operator) {
    const count = this.store.acknowledgeAllAlerts(operatorName(operator));
    if (count > 0) {
      this.store.addIncident({
        nodeId: null,
        nodeName: 'Command console',
        type: 'acknowledgement',
        severity: 'moderate',
        title: `${count} active alert${count === 1 ? '' : 's'} acknowledged`,
        detail: `${operatorName(operator)} acknowledged all active warnings from the command console.`,
        source: 'operator',
        status: 'acknowledged',
        metadata: { count, operator: operatorName(operator) },
      });
    }
    return count;
  }

  issueEvacuation({ nodeId = null, reason, operator }) {
    const current = this.store.getState('evacuation', { active: false });
    if (current.active) {
      throw new CommandError('An evacuation order is already active. Issue an all-clear first.', 409);
    }

    const targetNode = nodeId ? this.store.getNode(nodeId) : null;
    if (nodeId && !targetNode) throw new CommandError('Sensor node not found', 404);

    const scope = targetNode ? targetNode.id : 'all';
    const targetName = targetNode ? targetNode.name : `${SITE.name} — all sectors`;
    const issuedAt = nowIso();
    const alert = this.store.createAlert({
      id: createId('alt'),
      nodeId: targetNode?.id ?? null,
      nodeName: targetNode?.name ?? SITE.name,
      type: 'evacuation',
      severity: 'severe',
      title: `EVACUATION ORDER — ${targetName}`,
      message: `${reason} Move to the nearest high-ground assembly point. Follow marked evacuation routes and avoid river crossings.`,
      status: 'active',
      source: 'operator',
      metadata: {
        scope,
        operator: operatorName(operator),
        assemblyPoints: ['Panchavati High School', 'Nashik Road Community Hall', 'Darna Dam Upper Plateau'],
      },
    });

    const state = {
      active: true,
      scope,
      targetName,
      reason,
      issuedAt,
      issuedBy: operatorName(operator),
      alertId: alert.id,
    };
    this.store.setState('evacuation', state);
    this.store.setState('siren', { enabled: true, updatedAt: issuedAt });

    const incident = this.store.addIncident({
      nodeId: targetNode?.id ?? null,
      nodeName: targetNode?.name ?? SITE.name,
      type: 'evacuation',
      severity: 'severe',
      title: `Evacuation order issued for ${targetName}`,
      detail: `${operatorName(operator)} issued a mandatory evacuation order. Reason: ${reason}`,
      source: 'operator',
      status: 'open',
      metadata: { alertId: alert.id, scope, assemblyPoints: ['Panchavati High School', 'Nashik Road Community Hall'] },
    });

    return { alert, state, incident };
  }

  clearEvacuation(operator) {
    const current = this.store.getState('evacuation', { active: false });
    if (!current.active) {
      throw new CommandError('No evacuation order is active', 409);
    }

    this.store.resolveAlertsByType('evacuation');
    const state = {
      active: false,
      scope: null,
      targetName: null,
      reason: null,
      issuedAt: current.issuedAt,
      clearedAt: nowIso(),
      clearedBy: operatorName(operator),
    };
    this.store.setState('evacuation', state);
    this.store.setState('siren', { enabled: false, updatedAt: state.clearedAt });

    const incident = this.store.addIncident({
      nodeId: null,
      nodeName: 'Command console',
      type: 'evacuation',
      severity: 'moderate',
      title: 'Evacuation order cleared',
      detail: `${operatorName(operator)} issued the all-clear. Emergency channels returned to monitoring mode.`,
      source: 'operator',
      status: 'resolved',
      metadata: { previousScope: current.scope },
    });

    return { state, incident };
  }

  overrideRisk({ nodeId, level, note, durationMinutes, operator }) {
    const node = this.store.getNode(nodeId);
    if (!node) throw new CommandError('Sensor node not found', 404);

    const until = new Date(Date.now() + durationMinutes * 60 * 1000).toISOString();
    const updated = this.store.setOverride(nodeId, {
      level,
      note,
      by: operatorName(operator),
      until,
    });

    const incident = this.store.addIncident({
      nodeId: node.id,
      nodeName: node.name,
      type: 'command',
      severity: level,
      title: `Risk state overridden to ${level.toUpperCase()}`,
      detail: `${operatorName(operator)} overrode ${node.name} for ${durationMinutes} minutes. Operator note: ${note}`,
      source: 'operator',
      status: 'monitoring',
      metadata: {
        previousLevel: node.risk.level,
        overrideLevel: level,
        until,
        operator: operatorName(operator),
      },
    });

    return { node: updated, incident };
  }

  clearOverride(nodeId, operator) {
    const node = this.store.getNode(nodeId);
    if (!node) throw new CommandError('Sensor node not found', 404);
    if (!node.override) throw new CommandError('No override is active for this node', 409);

    const previousLevel = node.override.level;
    const updated = this.store.clearOverride(nodeId);
    const incident = this.store.addIncident({
      nodeId: node.id,
      nodeName: node.name,
      type: 'command',
      severity: 'moderate',
      title: 'Risk override removed',
      detail: `${operatorName(operator)} restored automatic risk evaluation for ${node.name}.`,
      source: 'operator',
      status: 'resolved',
      metadata: { previousLevel, operator: operatorName(operator) },
    });

    return { node: updated, incident };
  }

  triggerSos(nodeId, operator) {
    const node = this.store.getNode(nodeId);
    if (!node) throw new CommandError('Sensor node not found', 404);

    const activeSos = this.store.getActiveAlertForNode(node.id, 'sos');
    if (activeSos) throw new CommandError('A manual SOS is already active for this node', 409);

    const alert = this.store.createAlert({
      nodeId: node.id,
      nodeName: node.name,
      type: 'sos',
      severity: 'severe',
      title: `Manual SOS — ${node.name}`,
      message: `Manual SOS exercised from ${node.location}. GPS ${node.lat.toFixed(5)}, ${node.lon.toFixed(5)}. Treat as a live emergency until cleared.`,
      status: 'active',
      source: 'operator',
      metadata: { drill: true, operator: operatorName(operator), battery: node.latest.battery },
    });

    const incident = this.store.addIncident({
      nodeId: node.id,
      nodeName: node.name,
      type: 'sos',
      severity: 'severe',
      title: `Manual SOS test — ${node.name}`,
      detail: `${operatorName(operator)} triggered the node SOS channel from the command console.`,
      source: 'operator',
      status: 'open',
      metadata: { alertId: alert.id, drill: true },
    });

    return { alert, incident };
  }

  setSiren(enabled, operator) {
    const state = { enabled: Boolean(enabled), updatedAt: nowIso(), operator: operatorName(operator) };
    this.store.setState('siren', state);
    this.store.addIncident({
      nodeId: null,
      nodeName: 'Command console',
      type: 'command',
      severity: enabled ? 'high' : 'moderate',
      title: enabled ? 'Evacuation siren activated' : 'Evacuation siren silenced',
      detail: `${operatorName(operator)} ${enabled ? 'activated' : 'silenced'} the public siren channel.`,
      source: 'operator',
      status: enabled ? 'open' : 'resolved',
      metadata: { enabled },
    });
    return state;
  }
}
