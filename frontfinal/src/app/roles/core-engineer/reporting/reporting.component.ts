import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-core-reporting',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reporting.component.html',
  styleUrls: ['./reporting.component.scss']
})
export class CoreReportingComponent {
  reportTitle = '';
  selectedZone = 'all';
  dateFrom = '2026-04-01';
  dateTo = '2026-05-10';
  
  // Report sections checkboxes
  globalKpi = true;
  shapExplainability = true;
  qosTrends = false;
  latencyThroughput = false;
  executiveSummary = false;

  // Report history data
  reportHistory = [
    {
      name: 'CORE Performance — May 2026',
      type: 'Performance',
      scope: 'All Zones',
      generated: 'May 10, 2026 · 08:00',
      format: 'PDF',
      status: 'done'
    },
    {
      name: 'Zone Comparison — Mobile vs Hbahn',
      type: 'Comparative',
      scope: 'Zone vs Zone',
      generated: 'May 07, 2026 · 14:20',
      format: 'PDF',
      status: 'done'
    },
    {
      name: 'QoS Degradation Report — Hbahn',
      type: 'QoS',
      scope: 'Hbahn',
      generated: 'May 02, 2026 · 11:10',
      format: 'PDF',
      status: 'pending'
    }
  ];

  generatePDF() {
    const selectedSections = this.getSelectedSections();
    const reportData = {
      title: this.reportTitle || 'CORE Network Performance Report',
      zone: this.selectedZone,
      dateFrom: this.dateFrom,
      dateTo: this.dateTo,
      sections: selectedSections
    };
    
    console.log('Generating PDF report:', reportData);
    alert(`Report generated: ${reportData.title}\nZone: ${reportData.zone}\nSections: ${selectedSections.length} included`);
  }

  getSelectedSections(): string[] {
    const sections = [];
    if (this.globalKpi) sections.push('Global KPI Dashboard');
    if (this.shapExplainability) sections.push('SHAP Explainability');
    if (this.qosTrends) sections.push('QoS Degradation Trends');
    if (this.latencyThroughput) sections.push('Latency & Throughput');
    if (this.executiveSummary) sections.push('Executive Summary');
    return sections;
  }

  getSelectedSectionsCount(): number {
    return this.getSelectedSections().length;
  }

  getEstimatedPages(): number {
    const basePages = 8;
    const sectionPages = this.getSelectedSectionsCount() * 0.5;
    return Math.round(basePages + sectionPages);
  }

  downloadReport(reportName: string) {
    console.log('Downloading report:', reportName);
    alert(`Downloading: ${reportName}`);
  }

  viewReport(reportName: string) {
    console.log('Viewing report:', reportName);
    alert(`Opening: ${reportName}`);
  }
}
