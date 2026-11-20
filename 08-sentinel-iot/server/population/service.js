export class PopulationService {
  constructor() {
    this.populationData = new Map();
  }

  getExposedPopulation(riskLevel, area) {
    // Estimates based on risk level
    const multipliers = { low: 0, moderate: 0.1, high: 0.6, severe: 1.0 };
    const basePopulation = area || 10000;
    return Math.round(basePopulation * (multipliers[riskLevel] || 0));
  }

  getVillageInfo(lat, lon) {
    // Return mock village/city/town info
    return {
      type: 'town',
      name: 'Nashik',
      district: 'Nashik',
      state: 'Maharashtra',
      population: 1486053,
      pincode: '422001'
    };
  }
}
