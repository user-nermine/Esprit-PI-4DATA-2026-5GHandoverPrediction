import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-reporting',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reporting.component.html',
  styleUrls: ['./reporting.component.scss']
})
export class ReportingComponent {

  reportTitle = '5G Handover ML Platform — Weekly Report';
  reportType  = 'Weekly Executive Summary';
  dateFrom    = '2026-04-14';
  dateTo      = '2026-04-20';
  selectedZones: string[] = ['Zone A', 'Zone B', 'Zone C'];
  engineerNotes = '';

  // Propriétés pour les sections d'inclusion
  criticalAlerts = true;
  geographicCoordinates = true;

  sections = [
    { name: 'KPI Summary (RSRP, SINR, RSRQ)',       checked: true  },
    { name: 'Handover Success/Failure Analysis',      checked: true  },
    { name: 'Anomaly Detection Report',               checked: true  },
    { name: 'Incident Log',                           checked: true  },
    { name: 'ML Model Performance (AUC, F1)',         checked: true  },
    { name: 'SHAP Explainability Charts',             checked: true  },
    { name: 'Zone-level Breakdown',                   checked: true  },
    { name: 'Optimization Recommendations',           checked: true  },
    { name: 'Engineer Notes & Decisions',             checked: true  }
  ];

  history = [
    { title: 'NOC Weekly Report',       type: 'Weekly Executive Summary', period: '07/04 – 14/04', zones: 'A, B, C', format: 'PDF',   date: '14/04/2026' },
    { title: 'Incident Zone C',         type: 'Incident Report',          period: '24/04',          zones: 'C',       format: 'PDF',   date: '24/04/2026' },
    { title: 'ML Performance BiLSTM',   type: 'ML Performance Report',    period: '01/04 – 20/04', zones: 'Toutes',  format: 'Excel', date: '22/04/2026' },
    { title: 'Zone Analysis Hebdo',     type: 'Zone Analysis Report',     period: '14/04 – 20/04', zones: 'A, B',    format: 'Mail',  date: '20/04/2026' },
  ];

  generatePDF() {
    alert(`PDF généré : "${this.reportTitle}"\nSections : ${this.sections.filter(s => s.checked).length} sélectionnées\nZones : ${this.selectedZones.join(', ')}`);
  }

  exportExcel() {
    alert(`Export Excel : "${this.reportTitle}"\nPériode : ${this.dateFrom} → ${this.dateTo}`);
  }

  sendEmail() {
    alert(`Rapport envoyé par email !\nDestinataire : noc-team@invictus.com\nTitre : ${this.reportTitle}`);
  }
}