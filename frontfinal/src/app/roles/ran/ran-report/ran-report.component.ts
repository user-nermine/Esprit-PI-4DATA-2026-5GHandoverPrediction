import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

interface ReportSection {
  id: string;
  label: string;
  checked: boolean;
}

interface HoFailure {
  cellId: string;
  zone: string;
  hoType: string;
  failureRate: number;
  rsrp: number;
  sinr: number;
  cause: string;
  severity: 'critical' | 'high' | 'medium';
  status: string;
}

interface Recommendation {
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
}

interface ReportHistory {
  date: string;
  title: string;
  type: string;
  typeClass: string;
  pages: number;
  status: string;
  statusClass: string;
}

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  selector: 'app-ran-report',
  templateUrl: './ran-report.component.html',
  styleUrls: ['./ran-report.component.scss']
})
export class RanReportComponent {
  reportTitle = 'RAN Signal Degradation Report';
  environment = 'production';
  dateFrom = '2025-01-01';
  dateTo = '2025-01-31';

  sections: ReportSection[] = [
    { id: 'kpi-overview', label: 'KPI Overview', checked: true },
    { id: 'signal-quality', label: 'Signal Quality Analysis', checked: true },
    { id: 'ho-analysis', label: 'HO Failure Analysis', checked: true },
    { id: 'zone-coverage', label: 'Zone Coverage Map', checked: false },
    { id: 'anomaly-detect', label: 'Anomaly Detection', checked: true },
    { id: 'trend-analysis', label: 'Trend Analysis', checked: false },
    { id: 'recommendations', label: 'Recommendations', checked: true },
    { id: 'raw-data', label: 'Raw Data Export', checked: false }
  ];

  kpiRows = [
    { label: 'Avg RSRP', value: -88, unit: 'dBm', pct: 62, color: 'cyan' },
    { label: 'Avg RSRQ', value: -11.2, unit: 'dB', pct: 56, color: 'purple' },
    { label: 'Avg SINR', value: 14.3, unit: 'dB', pct: 71, color: 'green' },
    { label: 'HO Success', value: 91.6, unit: '%', pct: 91, color: 'green' },
    { label: 'HO Failure', value: 8.4, unit: '%', pct: 8, color: 'red' },
    { label: 'Ping-Pong', value: 3.2, unit: '%', pct: 32, color: 'orange' }
  ];

  hoFailures: HoFailure[] = [
    { cellId: 'CELL-0471', zone: 'Zone A', hoType: 'X2', failureRate: 18.4, rsrp: -102, sinr: 4.1, cause: 'Weak RSRP', severity: 'critical', status: 'Open' },
    { cellId: 'CELL-0283', zone: 'Zone B', hoType: 'S1', failureRate: 14.7, rsrp: -98, sinr: 6.3, cause: 'Ping-Pong', severity: 'high', status: 'Open' },
    { cellId: 'CELL-0159', zone: 'Zone C', hoType: 'X2', failureRate: 11.2, rsrp: -95, sinr: 7.8, cause: 'Missing Neighbor', severity: 'high', status: 'In Review' },
    { cellId: 'CELL-0392', zone: 'Zone A', hoType: 'X2', failureRate: 8.6, rsrp: -91, sinr: 9.4, cause: 'Interference', severity: 'medium', status: 'Resolved' },
    { cellId: 'CELL-0614', zone: 'Zone D', hoType: 'S1', failureRate: 6.1, rsrp: -89, sinr: 11.2, cause: 'Load Imbalance', severity: 'medium', status: 'Resolved' }
  ];

  recommendations: Recommendation[] = [
    { priority: 'high', title: 'Optimize CELL-0471 TX Power', description: 'Increase TX power by 3 dB on CELL-0471 to address weak RSRP causing 18.4% HO failure rate in Zone A.' },
    { priority: 'high', title: 'Add Missing Neighbor Relations', description: 'Configure 3 missing neighbor relations for CELL-0159 to eliminate ping-pong handovers and reduce failure rate.' },
    { priority: 'medium', title: 'Adjust Handover Thresholds', description: 'Tune A3 offset from +3 dB to +1 dB for Zone B cells to reduce premature handover triggers.' },
    { priority: 'low', title: 'Enable Carrier Aggregation', description: 'Enable CA on 4 cells in Zone C to improve throughput and reduce interference from neighboring cells.' }
  ];

  history: ReportHistory[] = [
    { date: '2025-01-15', title: 'Weekly RAN Report', type: 'Weekly', typeClass: 'cyan', pages: 24, status: 'Completed', statusClass: 'green' },
    { date: '2025-01-08', title: 'HO Analysis Report', type: 'Custom', typeClass: 'purple', pages: 18, status: 'Completed', statusClass: 'green' },
    { date: '2025-01-01', title: 'Monthly Summary', type: 'Monthly', typeClass: 'orange', pages: 36, status: 'Completed', statusClass: 'green' },
    { date: '2024-12-25', title: 'Anomaly Alert Report', type: 'Alert', typeClass: 'red', pages: 12, status: 'Archived', statusClass: 'gray' }
  ];

  get estimatedPages(): number {
    return this.sections.filter(s => s.checked).length * 3 + 4;
  }

  get selectedSections(): ReportSection[] {
    return this.sections.filter(s => s.checked);
  }

  goBack(): void {
    this.router.navigate(['/ran-engineer/anomaly']);
  }

  generateReport(): void {
    console.log('Generating report:', { title: this.reportTitle, environment: this.environment, sections: this.selectedSections });
  }

  downloadReport(item: ReportHistory): void {
    console.log('Downloading:', item.title);
  }

  viewReport(item: ReportHistory): void {
    console.log('Viewing:', item.title);
  }

  constructor(private router: Router) {}
}
