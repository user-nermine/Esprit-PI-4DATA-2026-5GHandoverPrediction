import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EnhancedStreamlitService, PerformanceMetrics } from '../../services/enhanced-streamlit.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-performance-indicator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="performance-indicator" [class]="getStatusClass()">
      <div class="indicator-header">
        <span class="status-dot" [class]="getStatusClass()"></span>
        <span class="status-text">{{getStatusText()}}</span>
        <span class="response-time">{{responseTime}}ms</span>
      </div>
      <div class="system-health" *ngIf="showDetails">
        <div class="health-metric">
          <span class="metric-label">CPU:</span>
          <span class="metric-value">{{systemHealth?.cpuPercent || 0}}%</span>
        </div>
        <div class="health-metric">
          <span class="metric-label">Memory:</span>
          <span class="metric-value">{{systemHealth?.memoryPercent || 0}}%</span>
        </div>
        <div class="health-metric">
          <span class="metric-label">Disk:</span>
          <span class="metric-value">{{systemHealth?.diskUsage || 0}}%</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .performance-indicator {
      position: fixed;
      top: 20px;
      right: 20px;
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      z-index: 1000;
      font-size: 12px;
      min-width: 200px;
      backdrop-filter: blur(10px);
    }

    .indicator-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }

    .status-dot.healthy {
      background-color: #10b981;
    }

    .status-dot.degraded {
      background-color: #f59e0b;
    }

    .status-dot.critical {
      background-color: #ef4444;
    }

    .status-text {
      font-weight: 600;
      flex: 1;
    }

    .response-time {
      color: #666;
      font-size: 11px;
    }

    .system-health {
      border-top: 1px solid #e0e0e0;
      padding-top: 8px;
      margin-top: 8px;
    }

    .health-metric {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .metric-label {
      color: #666;
    }

    .metric-value {
      font-weight: 500;
    }

    .performance-indicator.healthy {
      border-color: #10b981;
    }

    .performance-indicator.degraded {
      border-color: #f59e0b;
    }

    .performance-indicator.critical {
      border-color: #ef4444;
    }

    @keyframes pulse {
      0% {
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
      100% {
        opacity: 1;
      }
    }
  `]
})
export class PerformanceIndicatorComponent implements OnInit, OnDestroy {
  responseTime: number = 0;
  status: 'healthy' | 'degraded' | 'critical' = 'healthy';
  systemHealth: any = null;
  showDetails: boolean = false;
  private performanceSubscription: Subscription = new Subscription();

  constructor(private enhancedStreamlitService: EnhancedStreamlitService) {}

  ngOnInit(): void {
    // Subscribe to performance metrics
    this.performanceSubscription = this.enhancedStreamlitService.performanceMetrics$.subscribe(
      (metrics: PerformanceMetrics) => {
        this.responseTime = Math.round(metrics.responseTime);
        this.status = metrics.status;
        this.systemHealth = metrics.systemHealth;
      }
    );

    // Toggle details on hover
    setTimeout(() => {
      const indicator = document.querySelector('.performance-indicator');
      if (indicator) {
        indicator.addEventListener('mouseenter', () => {
          this.showDetails = true;
        });
        indicator.addEventListener('mouseleave', () => {
          this.showDetails = false;
        });
      }
    }, 100);
  }

  ngOnDestroy(): void {
    if (this.performanceSubscription) {
      this.performanceSubscription.unsubscribe();
    }
  }

  getStatusClass(): string {
    return this.status;
  }

  getStatusText(): string {
    switch (this.status) {
      case 'healthy':
        return 'System Healthy';
      case 'degraded':
        return 'Performance Degraded';
      case 'critical':
        return 'Performance Critical';
      default:
        return 'Unknown';
    }
  }
}
