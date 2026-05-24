import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';

export interface ReportRequest {
  reportType: string; // PDF, EXCEL
  template: string; // PERFORMANCE_SUMMARY, CLUSTER_ANALYSIS, HANDOVER_REPORT, PREDICTION_ANALYSIS
  dateRange: {
    startDate: string;
    endDate: string;
  };
  clusterIds?: number[];
  filters?: Record<string, any>;
  format?: string; // DETAILED, SUMMARY, CHARTS_ONLY
  language?: string; // EN, FR
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
}

export interface ReportFormat {
  code: string;
  name: string;
  extension: string;
}

export interface ReportPreview {
  template: string;
  pages: number;
  estimatedSize: string;
  generationTime: string;
  sampleData: any;
}

@Injectable({ providedIn: 'root' })
export class ReportingService {
  private readonly API_URL = 'http://localhost:8083';
  
  private templatesSubject = new BehaviorSubject<ReportTemplate[]>([]);
  private formatsSubject = new BehaviorSubject<ReportFormat[]>([]);
  
  public templates$ = this.templatesSubject.asObservable();
  public formats$ = this.formatsSubject.asObservable();

  constructor(private http: HttpClient) {
    console.log('📋 ReportingService initialized for PDF/Excel generation');
    this.loadInitialData();
  }

  private loadInitialData() {
    // Load available templates
    this.getAvailableTemplates().subscribe({
      next: (templates) => {
        console.log('📊 Report templates loaded:', templates.length, 'templates');
        this.templatesSubject.next(templates);
      },
      error: (error) => {
        console.error('❌ Failed to load templates:', error);
        this.useFallbackTemplates();
      }
    });

    // Load supported formats
    this.getSupportedFormats().subscribe({
      next: (formats) => {
        console.log('📄 Report formats loaded:', formats.length, 'formats');
        this.formatsSubject.next(formats);
      },
      error: (error) => {
        console.error('❌ Failed to load formats:', error);
        this.useFallbackFormats();
      }
    });
  }

  // Generate report (PDF or Excel)
  generateReport(request: ReportRequest): Observable<Blob> {
    console.log('📋 Generating report:', request.template, 'as', request.reportType);
    
    return this.http.post(`${this.API_URL}/api/v1/reporting/generate`, request, {
      responseType: 'blob'
    });
  }

  // Get available report templates
  getAvailableTemplates(): Observable<ReportTemplate[]> {
    return this.http.get<ReportTemplate[]>(`${this.API_URL}/api/v1/reporting/templates`);
  }

  // Get supported formats
  getSupportedFormats(): Observable<ReportFormat[]> {
    return this.http.get<ReportFormat[]>(`${this.API_URL}/api/v1/reporting/formats`);
  }

  // Preview report before generation
  previewReport(template: string): Observable<ReportPreview> {
    console.log('👁️ Generating preview for template:', template);
    return this.http.get<ReportPreview>(`${this.API_URL}/api/v1/reporting/preview?template=${template}`);
  }

  // Download generated report
  downloadReport(reportData: Blob, filename: string): void {
    const url = window.URL.createObjectURL(reportData);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    console.log('📥 Report downloaded:', filename);
  }

  // Health check
  healthCheck(): Observable<any> {
    return this.http.get(`${this.API_URL}/api/v1/reporting/health`);
  }

  // Helper methods
  private useFallbackTemplates() {
    const fallbackTemplates: ReportTemplate[] = [
      {
        id: 'PERFORMANCE_SUMMARY',
        name: 'Performance Summary',
        description: 'Overall network performance metrics'
      },
      {
        id: 'CLUSTER_ANALYSIS',
        name: 'Cluster Analysis',
        description: 'Detailed analysis of specific clusters'
      },
      {
        id: 'HANDOVER_REPORT',
        name: 'Handover Report',
        description: 'Handover statistics and analysis'
      },
      {
        id: 'PREDICTION_ANALYSIS',
        name: 'Prediction Analysis',
        description: 'ML model performance and predictions'
      }
    ];

    this.templatesSubject.next(fallbackTemplates);
  }

  private useFallbackFormats() {
    const fallbackFormats: ReportFormat[] = [
      {
        code: 'PDF',
        name: 'PDF Document',
        extension: '.pdf'
      },
      {
        code: 'EXCEL',
        name: 'Excel Spreadsheet',
        extension: '.xlsx'
      }
    ];

    this.formatsSubject.next(fallbackFormats);
  }

  // Create report request with default values
  createReportRequest(
    template: string, 
    reportType: string = 'PDF',
    clusterIds?: number[]
  ): ReportRequest {
    const now = new Date();
    const lastWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    return {
      reportType,
      template,
      dateRange: {
        startDate: lastWeek.toISOString(),
        endDate: now.toISOString()
      },
      clusterIds: clusterIds || [77, 78, 79, 80, 81],
      format: 'DETAILED',
      language: 'EN'
    };
  }

  // Generate filename for download
  generateFilename(template: string, reportType: string): string {
    const timestamp = new Date().toISOString().replace(/:/g, '-').substring(0, 19);
    const extension = reportType.toLowerCase() === 'pdf' ? '.pdf' : '.xlsx';
    return `donext_${template.toLowerCase()}_${timestamp}${extension}`;
  }
}

