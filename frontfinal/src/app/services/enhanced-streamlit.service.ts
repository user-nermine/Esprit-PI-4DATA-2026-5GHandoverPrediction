import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, timer, Subject } from 'rxjs';
import { catchError, map, retry, shareReplay, distinctUntilChanged } from 'rxjs/operators';

export interface PerformanceMetrics {
  responseTime: number;
  status: 'healthy' | 'degraded' | 'critical';
  uptime: string;
  systemHealth: SystemHealth;
}

export interface SystemHealth {
  cpuPercent: number;
  memoryPercent: number;
  diskUsage: number;
}

export interface ApiResponse<T> {
  timestamp: string;
  data: T;
  performance?: PerformanceMetrics;
}

@Injectable({
  providedIn: 'root'
})
export class EnhancedStreamlitService {
  private readonly API_BASE_URL = 'http://localhost:5000/api';
  private readonly RETRY_ATTEMPTS = 3;
  private readonly RETRY_DELAY = 1000;
  private readonly CACHE_DURATION = 30000; // 30 seconds
  
  private cache = new Map<string, { data: any; timestamp: number }>();
  private performanceSubject = new Subject<PerformanceMetrics>();
  
  // Performance metrics observable
  public performanceMetrics$ = this.performanceSubject.asObservable();

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'X-Client-Version': '2.0.0',
      'X-Request-ID': this.generateRequestId()
    });
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getCacheKey(endpoint: string): string {
    const now = new Date();
    const minuteKey = `${now.getHours()}_${now.getMinutes()}`;
    return `${endpoint}_${minuteKey}`;
  }

  private isCacheValid(timestamp: number): boolean {
    return Date.now() - timestamp < this.CACHE_DURATION;
  }

  private getCachedData<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (cached && this.isCacheValid(cached.timestamp)) {
      return cached.data;
    }
    if (cached) {
      this.cache.delete(key);
    }
    return null;
  }

  private setCachedData<T>(key: string, data: T): void {
    this.cache.set(key, { data, timestamp: Date.now() });
    
    // Clean old cache entries
    if (this.cache.size > 50) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Client error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Server error: ${error.status} - ${error.message}`;
    }
    
    console.error('Enhanced Streamlit Service Error:', errorMessage, error);
    return throwError(() => new Error(errorMessage));
  }

  private measurePerformance<T>(endpoint: string): (source: Observable<T>) => Observable<T> {
    return (source) => {
      const startTime = performance.now();
      
      return source.pipe(
        map(data => {
          const endTime = performance.now();
          const responseTime = endTime - startTime;
          
          // Update performance metrics
          this.performanceSubject.next({
            responseTime,
            status: responseTime < 500 ? 'healthy' : responseTime < 1000 ? 'degraded' : 'critical',
            uptime: '0s', // This would be calculated from server response
            systemHealth: { cpuPercent: 0, memoryPercent: 0, diskUsage: 0 }
          });
          
          return data;
        })
      );
    };
  }

  // Enhanced API methods with caching and performance monitoring
  getHealthCheck(): Observable<any> {
    const cacheKey = this.getCacheKey('health');
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return new Observable(observer => {
        observer.next(cached);
        observer.complete();
      });
    }

    return this.http.get(`${this.API_BASE_URL}/health`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('health'),
      map(response => {
        this.setCachedData(cacheKey, response);
        return response;
      }),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  getKpiMetrics(): Observable<any> {
    const cacheKey = this.getCacheKey('kpi_metrics');
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return new Observable(observer => {
        observer.next(cached);
        observer.complete();
      });
    }

    return this.http.get(`${this.API_BASE_URL}/kpi/metrics`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('kpi_metrics'),
      map(response => {
        this.setCachedData(cacheKey, response);
        return response;
      }),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  getAnomalyMetrics(): Observable<any> {
    const cacheKey = this.getCacheKey('anomaly_metrics');
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return new Observable(observer => {
        observer.next(cached);
        observer.complete();
      });
    }

    return this.http.get(`${this.API_BASE_URL}/anomaly/metrics`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('anomaly_metrics'),
      map(response => {
        this.setCachedData(cacheKey, response);
        return response;
      }),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  getDiagnosisData(): Observable<any> {
    const cacheKey = this.getCacheKey('diagnosis_data');
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return new Observable(observer => {
        observer.next(cached);
        observer.complete();
      });
    }

    return this.http.get(`${this.API_BASE_URL}/diagnosis/data`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('diagnosis_data'),
      map(response => {
        this.setCachedData(cacheKey, response);
        return response;
      }),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  getOptimizationRecommendations(): Observable<any> {
    const cacheKey = this.getCacheKey('optimization_recommendations');
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return new Observable(observer => {
        observer.next(cached);
        observer.complete();
      });
    }

    return this.http.get(`${this.API_BASE_URL}/optimization/recommendations`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('optimization_recommendations'),
      map(response => {
        this.setCachedData(cacheKey, response);
        return response;
      }),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  getPerformanceReport(): Observable<any> {
    return this.http.get(`${this.API_BASE_URL}/performance/report`, { headers: this.getHeaders() }).pipe(
      this.measurePerformance('performance_report'),
      retry({ count: this.RETRY_ATTEMPTS, delay: this.RETRY_DELAY }),
      catchError(this.handleError),
      shareReplay(1)
    );
  }

  // Utility methods for professional telecom operators
  clearCache(): void {
    this.cache.clear();
    console.log('Cache cleared for professional refresh');
  }

  getCacheSize(): number {
    return this.cache.size;
  }

  getSystemStatus(): Observable<string> {
    return timer(0, 30000).pipe( // Check every 30 seconds
      map(() => {
        const isHealthy = this.checkSystemHealth();
        return isHealthy ? 'healthy' : 'degraded';
      }),
      distinctUntilChanged()
    );
  }

  private checkSystemHealth(): boolean {
    // Check if we have recent successful API calls
    // This would be enhanced with actual health checks
    return true;
  }
}
