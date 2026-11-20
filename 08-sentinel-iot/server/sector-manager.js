import { getSectorNodes } from './sector-data.js';
import { getSector } from './sectors.js';

export class SectorManager {
  constructor(store) {
    this.store = store;
  }

  switchSector(code) {
    const sector = getSector(code);
    const nodes = getSectorNodes(code);
    
    // Clear existing nodes and load sector nodes
    const existing = this.store.listNodes();
    for (const node of existing) {
      this.store.db.prepare('DELETE FROM telemetry WHERE node_id = ?').run(node.id);
      this.store.db.prepare('DELETE FROM alerts WHERE node_id = ?').run(node.id);
      this.store.db.prepare('DELETE FROM incidents WHERE node_id = ?').run(node.id);
      this.store.db.prepare('DELETE FROM nodes WHERE id = ?').run(node.id);
    }
    
    this.store.transaction(() => {
      nodes.forEach((node) => this.store.insertNode(node));
      this.store.setSite(sector);
    });
    
    return { sector, nodes };
  }
}
