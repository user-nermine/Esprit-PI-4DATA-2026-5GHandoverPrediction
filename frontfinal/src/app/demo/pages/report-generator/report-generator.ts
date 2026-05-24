import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule, NgFor, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ReportingService, ReportTemplate, ReportRequest } from '../../../services/reporting.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-report-generator',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, NgFor], 
  templateUrl: './report-generator.html',
  styleUrl: './report-generator.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReportGeneratorComponent implements OnInit, OnDestroy {

  private apiSubscription: Subscription = new Subscription();
  
  // Real report data
  reportTemplates: ReportTemplate[] = [];
  selectedTemplate: string = 'PERFORMANCE_SUMMARY';
  selectedFormat: string = 'PDF';
  selectedClusters: number[] = [77, 78, 79, 80, 81];
  
  // Report generation state
  isGenerating: boolean = false;
  generatedReports: any[] = [];
  reportPreviews: any = {};
  
  // Report sections (dynamic based on template)
  sections: string[] = [];
  showPreview: boolean = false;
  observations: string = '';
  today: string = new Date().toLocaleString();

  // Properties for the new NOC-style form
  reportTitle: string = 'Performance Engineer Report';
  dateFrom: string = '';
  dateTo: string = '';
  selectedZones: string[] = [];
  
  // Checkbox properties for sections
  criticalAlerts: boolean = true;
  radioAnalytics: boolean = true;
  networkMetrics: boolean = true;
  explainableAI: boolean = false;
  executedModels: boolean = false;
  predictionOutcomes: boolean = true;
  
  // History data
  history: any[] = [
    { title: 'Performance Report', type: 'Performance', period: '2026-05-01 to 2026-05-06', zones: 'A, B, C', format: 'PDF', date: '2026-05-06 14:30' },
    { title: 'Network Analysis', type: 'Analysis', period: '2026-05-01 to 2026-05-06', zones: 'A, B', format: 'Excel', date: '2026-05-06 12:15' },
    { title: 'Handover Report', type: 'Optimization', period: '2026-04-25 to 2026-05-01', zones: 'A, B, C, D', format: 'PDF', date: '2026-05-01 16:45' }
  ];

  constructor(private router: Router, 
              private reportingService: ReportingService,
              private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.subscribeToReportingData();
    this.updateSections();
  }

  ngOnDestroy(): void {
    this.apiSubscription.unsubscribe();
  }

  private subscribeToReportingData() {
    // Subscribe to report templates
    const templatesSub = this.reportingService.templates$.subscribe(templates => {
      this.reportTemplates = templates;
      console.log('📋 Report Generator: Templates updated', templates.length, 'templates');
      this.cdr.detectChanges();
    });

    this.apiSubscription.add(templatesSub);
  }

  private updateSections() {
    // Dynamic sections based on selected template
    switch (this.selectedTemplate) {
      case 'PERFORMANCE_SUMMARY':
        this.sections = [
          'KPI Summary (RSRP, SINR, RSRQ)',
          'Network Performance Metrics',
          'Handover Success/Failure Analysis',
          'System Health Overview',
          'Performance Trends',
          'Optimization Recommendations'
        ];
        break;
      case 'CLUSTER_ANALYSIS':
        this.sections = [
          'Cluster KPIs Breakdown',
          'Signal Quality Analysis',
          'Traffic Distribution',
          'Performance Comparison',
          'Anomaly Detection',
          'Cluster-specific Recommendations'
        ];
        break;
      case 'HANDOVER_REPORT':
        this.sections = [
          'Handover Statistics',
          'Success/Failure Analysis',
          'Handover Types Breakdown',
          'Geographic Distribution',
          'Performance Trends',
          'Optimization Opportunities'
        ];
        break;
      case 'PREDICTION_ANALYSIS':
        this.sections = [
          'ML Model Performance',
          'Prediction Accuracy Metrics',
          'Model Comparison',
          'Feature Importance',
          'Confidence Analysis',
          'Model Recommendations'
        ];
        break;
      default:
        this.sections = [
          'KPI Summary (RSRP, SINR, RSRQ)',
          'Handover Success/Failure Analysis',
          'Anomaly Detection Report',
          'Incident Log',
          'ML Model Performance (AUC, F1)',
          'SHAP Explainability Charts',
          'Zone-level Breakdown',
          'Optimization Recommendations',
          'Engineer Notes & Decisions'
        ];
    }
  }

  // Report generation methods
  generatePDF() {
    this.generateReport('PDF');
  }

  generateExcel() {
    this.generateReport('EXCEL');
  }

  private generateReport(format: string) {
    this.isGenerating = true;
    this.selectedFormat = format;
    
    const request = this.createReportRequest();
    
    console.log(`📊 Generating ${format} report with template: ${this.selectedTemplate}`);
    
    this.reportingService.generateReport(request).subscribe({
      next: (blob) => {
        const filename = this.reportingService.generateFilename(this.selectedTemplate, format);
        this.reportingService.downloadReport(blob, filename);
        
        // Add to generated reports
        this.generatedReports.unshift({
          id: Date.now(),
          template: this.selectedTemplate,
          format: format,
          filename: filename,
          timestamp: new Date(),
          clusters: this.selectedClusters
        });
        
        this.isGenerating = false;
        console.log(`✅ ${format} report generated successfully`);
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error(`❌ Failed to generate ${format} report:`, error);
        this.isGenerating = false;
        this.cdr.detectChanges();
      }
    });
  }

  private createReportRequest(): ReportRequest {
    return this.reportingService.createReportRequest(
      this.selectedTemplate,
      this.selectedFormat,
      this.selectedClusters
    );
  }

  previewReport(template: string) {
    console.log('👁️ Generating preview for template:', template);
    
    this.reportingService.previewReport(template).subscribe({
      next: (preview) => {
        this.reportPreviews[template] = preview;
        this.showPreview = true;
        console.log('✅ Preview generated for:', template);
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('❌ Failed to generate preview:', error);
      }
    });
  }

  // Template and format selection
  onTemplateChange(template: string) {
    this.selectedTemplate = template;
    this.updateSections();
    console.log('📋 Template changed to:', template);
  }

  onFormatChange(format: string) {
    this.selectedFormat = format;
    console.log('📄 Format changed to:', format);
  }

  onClustersChange(clusters: number[]) {
    this.selectedClusters = clusters;
    console.log('🎯 Clusters changed to:', clusters);
  }

  // Utility methods
  getTemplateDescription(templateId: string): string {
    const template = this.reportTemplates.find(t => t.id === templateId);
    return template ? template.description : '';
  }

  getFormatIcon(format: string): string {
    return format === 'PDF' ? '📄' : '📊';
  }

  getReportIcon(template: string): string {
    switch (template) {
      case 'PERFORMANCE_SUMMARY': return '📈';
      case 'CLUSTER_ANALYSIS': return '🔍';
      case 'HANDOVER_REPORT': return '🔄';
      case 'PREDICTION_ANALYSIS': return '🤖';
      default: return '📋';
    }
  }

  getRecentReports(): any[] {
    return this.generatedReports.slice(0, 5);
  }

  deleteReport(reportId: number) {
    this.generatedReports = this.generatedReports.filter(r => r.id !== reportId);
    console.log('🗑️ Report deleted:', reportId);
  }

  // Navigation
  goToDashboard() {
    this.router.navigate(['/dashboard']);
  }

  goToMonitoring() {
    this.router.navigate(['/monitoring']);
  }
}