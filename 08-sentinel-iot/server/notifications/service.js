import { createId, nowIso } from '../utils.js';

export class NotificationService {
  constructor(store) {
    this.store = store;
    this.channels = ['sms', 'email', 'push', 'whatsapp'];
  }

  async sendAlert(alert, contacts = []) {
    const results = [];
    const message = this.buildMessage(alert);
    
    for (const contact of contacts) {
      for (const channel of this.channels) {
        if (contact[channel]) {
          const notification = {
            id: createId('NTF'),
            alertId: alert.id,
            channel,
            recipient: contact[channel],
            message,
            status: 'queued',
            createdAt: nowIso()
          };
          results.push(await this.dispatch(notification, channel));
        }
      }
    }
    return results;
  }

  buildMessage(alert) {
    return `[SENTINEL ALERT - ${alert.severity.toUpperCase()}] ${alert.title}. ${alert.message}. For emergencies call 112.`;
  }

  async dispatch(notification, channel) {
    // In production, integrate with Twilio, AWS SNS, SendGrid, Firebase etc.
    // For demo, log and mark as sent
    console.log(`[NOTIFY:${channel}] To: ${notification.recipient} | ${notification.message.substring(0, 60)}...`);
    return { ...notification, status: 'sent', sentAt: nowIso() };
  }

  getTemplates() {
    return {
      flood: 'FLOOD WARNING: {nodeName} - Water level {waterLevel}cm, Rain {rain}mm/h. Evacuate low-lying areas immediately.',
      landslide: 'LANDSLIDE WARNING: {nodeName} - Saturated slopes detected. Avoid steep areas.',
      sos: 'SOS EMERGENCY: {nodeName} requires immediate assistance. Location: {lat},{lon}',
      evacuation: 'EVACUATION ORDER: {scope} - {reason}. Proceed to nearest shelter immediately.'
    };
  }
}
