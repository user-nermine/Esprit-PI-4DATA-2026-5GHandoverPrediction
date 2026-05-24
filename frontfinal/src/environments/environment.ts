export const environment = {
  production: false,
  appVersion: '0.0.1',

  // API Gateway - point d'entree unique pour tous les services
  gatewayUrl: 'http://localhost:8083',

  // User Service (Auth + JWT + Users + Audit)
  apiUrl: 'http://localhost:8083/api',

  // Microservices URLs - tous via la Gateway
  apiUrls: {
    userService:          'http://localhost:8083',
    predictionService:    'http://localhost:8083',
    monitoringService:    'http://localhost:8083',
    explainabilityService:'http://localhost:8083',
    reportingService:     'http://localhost:8083',
    dataPipeline:         'http://localhost:8083',
  }
};
