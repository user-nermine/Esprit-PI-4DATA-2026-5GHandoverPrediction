import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class StreamlitService {
  private baseUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  // KPI Monitoring APIs
  getKpiMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/kpi/metrics`);
  }

  // Anomaly Detection APIs
  getAnomalyMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/anomaly/metrics`);
  }

  // Radio Diagnosis APIs
  getDiagnosisData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/diagnosis/data`);
  }

  // Optimization Support APIs
  getOptimizationRecommendations(): Observable<any> {
    return this.http.get(`${this.baseUrl}/optimization/recommendations`);
  }

  // Performance View APIs
  getPerformanceData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/performance/metrics`);
  }

  // Explainability APIs
  getExplainabilityData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/explainability/data`);
  }

  // Decision Support APIs
  getDecisionSupportData(): Observable<any> {
    return this.http.get(`${this.baseUrl}/decision-support/data`);
  }

  // Helper method pour générer de nouvelles données (pour tester)
  generateNewData(endpoint: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/generate/${endpoint}`, {});
  }
}
