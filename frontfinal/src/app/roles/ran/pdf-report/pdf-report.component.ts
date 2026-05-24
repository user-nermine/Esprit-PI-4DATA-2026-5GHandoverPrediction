import { Component, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-pdf-report',
  standalone: true,
  imports: [RouterModule, CommonModule],
  templateUrl: './pdf-report.component.html',
  styleUrls: ['./pdf-report.component.scss']
})
export class PdfReportComponent implements OnInit {

  reportType: string = '';
  reportTitle: string = '';
  reportData: any = {};
  loading = false;
  currentDateTime: string = '';
  
  // KPI Metrics for organized display
  kpiMetrics: any[] = [];

  constructor(private route: ActivatedRoute) { 
    this.currentDateTime = new Date().toLocaleString('fr-FR');
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.reportType = params['type'] || 'kpi';
      this.loadReportData();
    });
  }

  loadReportData(): void {
    this.loading = true;
    
    // Charger immédiatement les données sans délai
    switch(this.reportType) {
      case 'kpi':
        this.loadKpiReport();
        break;
      case 'anomaly':
        this.loadAnomalyReport();
        break;
      case 'diagnosis':
        this.loadDiagnosisReport();
        break;
      case 'optimization':
        this.loadOptimizationReport();
        break;
      default:
        this.loadKpiReport();
    }
  }

  loadKpiReport(): void {
    this.reportTitle = '5G Handover KPI Performance Report';
    this.reportData = {
      title: '5G Handover KPI Performance Report',
      date: new Date().toLocaleDateString('fr-FR'),
      period: 'Last 30 days',
      generatedBy: 'RAN Engineer',
      summary: {
        totalHandovers: 48320,
        successRate: 46580,
        failureRate: 1740,
        successRatePercent: 96.4,
        failureRatePercent: 3.6,
        aucScore: 0.943,
        f1Score: 0.921
      },
      kpiMetrics: [
        { name: 'Normal HO', value: 65, unit: '%', status: 'good' },
        { name: 'Ping-Pong', value: 15, unit: '%', status: 'warning' },
        { name: 'Early HO', value: 8, unit: '%', status: 'normal' },
        { name: 'Late HO', value: 7, unit: '%', status: 'warning' },
        { name: 'Failed', value: 5, unit: '%', status: 'critical' }
      ],
      cellPerformance: [
        { id: 'Zone A', successRate: 98.2, status: 'normal' },
        { id: 'Zone B', successRate: 94.1, status: 'warning' },
        { id: 'Zone C', successRate: 88.5, status: 'critical' },
        { id: 'Zone D', successRate: 92.3, status: 'warning' },
        { id: 'Zone E', successRate: 96.7, status: 'normal' }
      ],
      trends: {
        labels: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'],
        successRate: [0.91, 0.92, 0.93, 0.935, 0.94, 0.938, 0.942, 0.943],
        failureRate: [0.89, 0.90, 0.91, 0.91, 0.92, 0.915, 0.920, 0.921]
      }
    };
    
    // Organized KPI metrics for better display
    this.kpiMetrics = [
      { 
        icon: '📊', 
        label: 'Total HO Samples', 
        value: this.reportData.summary.totalHandovers.toLocaleString(), 
        change: 'Last 30 days',
        trend: 'neutral'
      },
      { 
        icon: '✅', 
        label: 'Successful HO', 
        value: this.reportData.summary.successRate.toLocaleString(), 
        change: `${this.reportData.summary.successRatePercent}%`,
        trend: 'up'
      },
      { 
        icon: '❌', 
        label: 'Failed HO', 
        value: this.reportData.summary.failureRate.toLocaleString(), 
        change: `${this.reportData.summary.failureRatePercent}%`,
        trend: 'down'
      },
      { 
        icon: '🎯', 
        label: 'Model AUC-ROC', 
        value: this.reportData.summary.aucScore.toString(), 
        change: '↑ XGBoost v2.3',
        trend: 'up'
      },
      { 
        icon: '📈', 
        label: 'F1-Score', 
        value: this.reportData.summary.f1Score.toString(), 
        change: '↑ +0.015 vs v2.2',
        trend: 'up'
      }
    ];
    
    this.loading = false;
  }

  loadAnomalyReport(): void {
    this.reportTitle = '5G Handover Anomaly Detection Report';
    this.reportData = {
      title: '5G Handover Anomaly Detection Report',
      date: new Date().toLocaleDateString('fr-FR'),
      period: 'Last 24 hours',
      generatedBy: 'RAN Engineer',
      summary: {
        activeAnomalies: 7,
        criticalAnomalies: 2,
        hoSpikes: 12,
        rsrpDropEvents: 18,
        maxAnomalyScore: 0.87
      },
      alerts: [
        { cell: 'gNB-004', type: 'HO Failure Spike', count: 45, severity: 'high', score: 0.87 },
        { cell: 'gNB-002', type: 'RSRP Drop', count: 23, severity: 'medium', score: 0.70 },
        { cell: 'gNB-007', type: 'Anomaly Score', count: 18, severity: 'medium', score: 0.60 },
        { cell: 'gNB-003', type: 'Ping-pong', count: 12, severity: 'low', score: 0.57 },
        { cell: 'gNB-001', type: 'Normal', count: 5, severity: 'low', score: 0.09 }
      ],
      anomalyScores: {
        labels: ['00h', '02h', '04h', '06h', '08h', '10h', '12h', '14h', '16h', '18h', '20h', '22h'],
        scores: [0.42, 0.38, 0.45, 0.51, 0.48, 0.55, 0.71, 0.85, 0.87, 0.63, 0.52, 0.46]
      },
      recommendations: [
        'Increase TTT timer on gNB-004 to reduce HO failures',
        'Adjust antenna tilt for gNB-002 to improve RSRP coverage',
        'Review neighbor relation list for gNB-003 to prevent ping-pong',
        'Monitor gNB-004 performance closely for next 72 hours'
      ]
    };
    // Désactiver le loading immédiatement
    this.loading = false;
  }

  loadDiagnosisReport(): void {
    this.reportTitle = '5G Handover Radio Diagnosis Report';
    this.reportData = {
      title: '5G Handover Radio Diagnosis Report',
      date: new Date().toLocaleDateString('fr-FR'),
      period: 'Last 24 hours',
      generatedBy: 'RAN Engineer',
      summary: {
        diagnosedCells: 5,
        criticalIssues: 1,
        warningIssues: 2,
        normalCells: 2,
        overallHealth: 72
      },
      cellDiagnosis: [
        { id: 'gNB-001', health: 85, issues: [], status: 'healthy' },
        { id: 'gNB-002', health: 68, issues: ['Coverage overlap', 'Ping-pong'], status: 'warning' },
        { id: 'gNB-003', health: 74, issues: ['Interference'], status: 'warning' },
        { id: 'gNB-004', health: 45, issues: ['HO failure', 'RSRP drop', 'Instability'], status: 'critical' },
        { id: 'gNB-005', health: 82, issues: [], status: 'healthy' }
      ],
      recommendations: [
        'Immediate intervention required for gNB-004',
        'Optimize antenna parameters for gNB-002 and gNB-003',
        'Monitor gNB-001 and gNB-005 performance',
        'Schedule maintenance check for critical cells'
      ]
    };
    // Désactiver le loading immédiatement
    this.loading = false;
  }

  loadOptimizationReport(): void {
    this.reportTitle = '5G Handover Optimization Support Report';
    this.reportData = {
      title: '5G Handover Optimization Support Report',
      date: new Date().toLocaleDateString('fr-FR'),
      period: 'Last 24 hours',
      generatedBy: 'RAN Engineer',
      summary: {
        recommendationsCount: 8,
        priorityHigh: 3,
        priorityMedium: 3,
        priorityLow: 2,
        estimatedImprovement: 15
      },
      recommendations: [
        { cell: 'gNB-004', action: 'Increase TTT timer', priority: 'high', impact: 'High' },
        { cell: 'gNB-002', action: 'Adjust antenna tilt', priority: 'high', impact: 'Medium' },
        { cell: 'gNB-003', action: 'Review neighbor list', priority: 'medium', impact: 'Medium' },
        { cell: 'gNB-005', action: 'Optimize CIO values', priority: 'medium', impact: 'Low' },
        { cell: 'All cells', action: 'Update handover parameters', priority: 'low', impact: 'Medium' }
      ],
      engineerNotes: 85,
      implementationPlan: [
        'Phase 1: Critical optimizations (gNB-004, gNB-002)',
        'Phase 2: Medium priority adjustments (gNB-003, gNB-005)',
        'Phase 3: Global parameter optimization',
        'Phase 4: Performance monitoring and validation'
      ]
    };
    // Désactiver le loading immédiatement
    this.loading = false;
  }

  downloadPDF(): void {
    // Simuler le téléchargement PDF
    const reportContent = this.generatePDFContent();
    const blob = new Blob([reportContent], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.reportTitle.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  generatePDFContent(): string {
    let content = `${this.reportData.title}\n`;
    content += `Generated: ${this.reportData.date}\n`;
    content += `Period: ${this.reportData.period}\n`;
    content += `Generated by: ${this.reportData.generatedBy}\n\n`;
    
    content += `=== EXECUTIVE SUMMARY ===\n`;
    if (this.reportData.summary) {
      Object.entries(this.reportData.summary).forEach(([key, value]) => {
        content += `${key}: ${value}\n`;
      });
    }
    
    return content;
  }

  printReport(): void {
    window.print();
  }

  getStatusClass(status: string): string {
    const classes = {
      good: 'success',
      warning: 'warning',
      critical: 'danger',
      normal: 'success',
      high: 'danger',
      medium: 'warning',
      low: 'info',
      healthy: 'success'
    };
    return classes[status] || 'info';
  }

  getHealthColor(score: number): string {
    if (score >= 80) return '#10B981';
    if (score >= 60) return '#059669';
    if (score >= 40) return '#F59E0B';
    return '#EF4444';
  }

  getPriorityClass(index: number): string {
    const priorities = ['high', 'high', 'medium', 'medium', 'low'];
    return priorities[index] || 'low';
  }

  getPriorityLabel(index: number): string {
    const labels = ['Critical', 'High', 'Medium', 'Low', 'Low'];
    return labels[index] || 'Low';
  }

  getTimeline(priority: string): string {
    const timelines = {
      'high': 'Immediate',
      'medium': '1-2 weeks',
      'low': '1 month'
    };
    return timelines[priority] || '2 weeks';
  }

  // Professional design methods
  getMetricClass(trend: string): string {
    const classes = {
      'up': 'metric-up',
      'down': 'metric-down',
      'neutral': 'metric-neutral'
    };
    return classes[trend] || 'metric-neutral';
  }

  getTrendArrow(trend: string): string {
    const arrows = {
      'up': '↑',
      'down': '↓',
      'neutral': '→'
    };
    return arrows[trend] || '→';
  }

  getProgressClass(status: string): string {
    const classes = {
      'good': 'progress-success',
      'warning': 'progress-warning',
      'critical': 'progress-danger',
      'normal': 'progress-info'
    };
    return classes[status] || 'progress-info';
  }

  getRowClass(status: string): string {
    const classes = {
      'normal': 'row-success',
      'warning': 'row-warning',
      'critical': 'row-danger',
      'healthy': 'row-success'
    };
    return classes[status] || 'row-info';
  }

  getImpactClass(score: number): string {
    if (score > 0.8) return 'impact-critical';
    if (score > 0.6) return 'impact-high';
    if (score > 0.4) return 'impact-medium';
    return 'impact-low';
  }

  getImpactLevel(score: number): string {
    if (score > 0.8) return 'Critical';
    if (score > 0.6) return 'High';
    if (score > 0.4) return 'Medium';
    return 'Low';
  }

  getPriorityIcon(index: number): string {
    const icons = ['🔴', '🟠', '🟡', '🟢', '🔵'];
    return icons[index] || '⚪';
  }

  getResourceRequirement(priority: string): string {
    const resources = {
      'high': '2 Engineers + Equipment',
      'medium': '1 Engineer + Support',
      'low': 'Standard Operations'
    };
    return resources[priority] || 'Standard Operations';
  }

  getPhaseDuration(index: number): string {
    const durations = ['Week 1-2', 'Week 3-4', 'Week 5-6', 'Week 7-8', 'Week 9-10'];
    return durations[index] || 'Week 11-12';
  }

  getReportId(): string {
    if (this.reportData.date) {
      return this.reportData.date.replace(/\//g, '');
    }
    return new Date().toISOString().split('T')[0].replace(/-/g, '');
  }
}
