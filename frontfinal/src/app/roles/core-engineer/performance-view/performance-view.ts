import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MonitoringService, ClusterMetric, SystemHealth, Alert } from '../../../services/monitoring.service';
import { PredictionService, ClusterPrediction } from '../../../services/prediction.service';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-performance-view',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './performance-view.html',
  styleUrl: './performance-view.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PerformanceViewComponent implements OnInit, OnDestroy {

  private apiSubscription: Subscription = new Subscription();
  
  selectedZone: string = 'Zone_77';
  availableZones: string[] = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81', 'Zone_82', 'Zone_83', 'Zone_84', 'Zone_85'];

  clusterMetrics: ClusterMetric[] = [];
  alerts: Alert[] = [];
  predictions: ClusterPrediction[] = [];
  systemHealth: SystemHealth | null = null;

  constructor(
    private router: Router,
    private monitoringService: MonitoringService,
    private predictionService: PredictionService,
    private cdr: ChangeDetectorRef,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    // Subscribe to monitoring data
    this.apiSubscription.add(
      this.monitoringService.metrics$.subscribe(metrics => {
        this.clusterMetrics = metrics;
        this.cdr.detectChanges();
      })
    );
    this.apiSubscription.add(
      this.monitoringService.systemHealth$.subscribe(health => {
        this.systemHealth = health;
        this.cdr.detectChanges();
      })
    );
    this.apiSubscription.add(
      this.monitoringService.alerts$.subscribe(alerts => {
        this.alerts = alerts;
        this.cdr.detectChanges();
      })
    );
  }

  ngOnDestroy(): void {
    this.apiSubscription.unsubscribe();
  }

  onZoneChange(): void {
    console.log('Zone changed to:', this.selectedZone);
  }

getSelectedZoneThroughput(): string {
    const clusterId = parseInt(this.selectedZone.replace('Zone_', ''));
    const metric = this.clusterMetrics.find(m => m.cluster_id === clusterId);
    return metric ? `${metric.network_throughput.toFixed(1)} Mbps` : '-- Mbps';
}

getSelectedZoneLatency(): string {
    const clusterId = parseInt(this.selectedZone.replace('Zone_', ''));
    const metric = this.clusterMetrics.find(m => m.cluster_id === clusterId);
    return metric ? `${metric.latency_ms.toFixed(1)} ms` : '-- ms';
}
}

