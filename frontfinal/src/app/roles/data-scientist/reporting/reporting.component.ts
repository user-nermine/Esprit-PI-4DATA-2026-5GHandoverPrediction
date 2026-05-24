import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-ds-reporting',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reporting.component.html',
  styleUrls: ['./reporting.component.scss']
})
export class DsReportingComponent {

  reportTitle = 'Monthly ML Performance Report — May 2026';
  targetModel = 'All Models';
  dateFrom    = '2026-04-01';
  dateTo      = '2026-05-10';
  selectedFormat = 'PDF';

  formats = ['PDF', 'Excel', 'JSON', 'HTML'];

  sections = [
    { id: 's1', name: 'Model Metrics',      icon: 'icon-bar-chart-2', checked: true  },
    { id: 's2', name: 'Drift Analysis',     icon: 'icon-activity',    checked: true  },
    { id: 's3', name: 'Confusion Matrix',   icon: 'icon-grid',        checked: true  },
    { id: 's4', name: 'SHAP Features',      icon: 'icon-layers',      checked: true  },
    { id: 's5', name: 'Retraining History', icon: 'icon-refresh-cw',  checked: false },
    { id: 's6', name: 'Validation Summary', icon: 'icon-shield',      checked: false },
    { id: 's7', name: 'ROC / PR Curves',    icon: 'icon-trending-up', checked: false },
    { id: 's8', name: 'Recommendations',    icon: 'icon-list',        checked: false },
  ];

  quickReports = [
    { title: 'Full ML Report',      sub: 'All sections · All models'            },
    { title: 'Drift Report Only',   sub: 'PSI · Feature drift · Alerts'         },
    { title: 'Validation Summary',  sub: 'Comparison · Decision · Verdict'      },
  ];

  history = [
    { name: 'Monthly ML Report — May 2026',    type: 'Full',        typeClass: 't-full',  model: 'All Models',     generated: 'May 10, 2026 · 08:14', by: 'Data Scientist', format: 'PDF',   status: 'Done',    statusClass: 's-done',    statusIcon: 'icon-check'   },
    { name: 'Drift Report — RSRP Critical',    type: 'Drift',       typeClass: 't-drift', model: 'HO Prediction',  generated: 'May 09, 2026 · 14:32', by: 'Data Scientist', format: 'PDF',   status: 'Done',    statusClass: 's-done',    statusIcon: 'icon-check'   },
    { name: 'Validation Report — TabNet v1.0', type: 'Validation',  typeClass: 't-valid', model: 'HO Prediction',  generated: 'May 08, 2026 · 10:05', by: 'Data Scientist', format: 'Excel', status: 'Done',    statusClass: 's-done',    statusIcon: 'icon-check'   },
    { name: 'Performance Report — April 2026', type: 'Performance', typeClass: 't-perf',  model: 'All Models',     generated: 'May 07, 2026 · 09:20', by: 'Data Scientist', format: 'PDF',   status: 'Pending', statusClass: 's-pending', statusIcon: 'icon-clock'   },
    { name: 'Drift Report — Next Best Cell',   type: 'Drift',       typeClass: 't-drift', model: 'Next Best Cell', generated: 'May 05, 2026 · 16:47', by: 'Data Scientist', format: 'JSON',  status: 'Failed',  statusClass: 's-failed',  statusIcon: 'icon-x'       },
  ];

  get estimatedPages(): number {
    return 4 + this.sections.filter(s => s.checked).length * 2;
  }

  generateReport(): void {
    const selected = this.sections.filter(s => s.checked).map(s => s.name).join(', ');
    alert(`Report generated!\nTitle: ${this.reportTitle}\nFormat: ${this.selectedFormat}\nSections: ${selected}`);
  }

  quickGenerate(title: string): void {
    alert(`Quick report generated: ${title}`);
  }

  downloadReport(r: any): void {
    if (r.status !== 'Pending') alert(`Downloading: ${r.name}`);
  }

  viewReport(r: any): void {
    alert(`Viewing: ${r.name}`);
  }
}
