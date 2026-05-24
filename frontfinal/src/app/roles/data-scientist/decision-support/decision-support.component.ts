import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule, NgFor, NgClass, NgStyle } from '@angular/common';
import { NgApexchartsModule } from 'ng-apexcharts';
import { Router, RouterModule } from '@angular/router';
import { PredictionService, ClusterPrediction, ModelPerformance, ModelComparison } from '../../../services/prediction.service';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-decision-support',
  standalone: true,
  imports: [
    CommonModule,
    NgApexchartsModule,
    RouterModule,
    FormsModule
  ],
  templateUrl: './decision-support.html',
  styleUrl: './decision-support.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DecisionSupportComponent implements OnInit, OnDestroy {

  private apiSubscription: Subscription = new Subscription();
  
  // Zone selection properties
  selectedZone: string = 'Zone_77'; // Default selection
  availableZones: string[] = ['Zone_77', 'Zone_78', 'Zone_79', 'Zone_80', 'Zone_81', 'Zone_82', 'Zone_83', 'Zone_84', 'Zone_85'];
  
  // Dashboard cells data
  dashboardCells: any[] = [];
  
  // Prediction data
  predictions: ClusterPrediction[] = [];
  modelPerformance: Record<string, ModelPerformance> = {};
  modelComparison: ModelComparison | null = null;
  bestModel: string = '';
  
  // Decision support specific data
  recommendations: any[] = [];
  riskAssessments: any[] = [];
  actionItems: any[] = [];
  
  // Template properties
  showNotes: boolean = false;
  showToast: boolean = false;
  selectedParam: any = null;
  parameters: any[] = [];
  strategies: any[] = [];
  predictiveAlerts: any[] = [];
  dso1Predictions: any[] = [];
  dso2Predictions: any[] = [];
  dso3Predictions: any[] = [];
  dso4Predictions: any[] = [];
  
  // Chart configurations
  predictionChart: any = {
    type: 'pie',
    height: 350
  };
  
  predictionSeries: any[] = [];
  
  modelChart: any = {
    type: 'radar',
    height: 350
  };
  
  modelSeries: any[] = [];

  constructor(private router: Router, 
              private predictionService: PredictionService,
              private cdr: ChangeDetectorRef) {
    // Initialize zone data
    this.loadSimulatorData();
  }

  ngOnInit(): void {
    this.subscribeToPredictionData();
    this.initializeTemplateData();
  }

  ngOnDestroy(): void {
    this.apiSubscription.unsubscribe();
  }

  private subscribeToPredictionData() {
    // Subscribe to predictions
    const predictionSub = this.predictionService.predictions$.subscribe(predictions => {
      this.predictions = predictions;
      this.updatePredictionCharts();
      this.generateRecommendations();
      console.log('🔮 Decision Support: Predictions updated', predictions.length, 'predictions');
      this.cdr.detectChanges();
    });

    // Subscribe to model performance
    const performanceSub = this.predictionService.modelPerformance$.subscribe(performance => {
      this.modelPerformance = performance;
      this.updateModelCharts();
      console.log('📊 Decision Support: Model performance updated');
      this.cdr.detectChanges();
    });

    // Subscribe to model comparison
    const comparisonSub = this.predictionService.modelComparison$.subscribe(comparison => {
      this.modelComparison = comparison;
      console.log('⚖️ Decision Support: Model comparison updated');
      this.cdr.detectChanges();
    });

    // Subscribe to best model
    const bestModelSub = this.predictionService.bestModel$.subscribe(bestModel => {
      this.bestModel = bestModel;
      console.log('🏆 Decision Support: Best model updated:', bestModel);
      this.cdr.detectChanges();
    });

    this.apiSubscription.add(predictionSub);
    this.apiSubscription.add(performanceSub);
    this.apiSubscription.add(comparisonSub);
    this.apiSubscription.add(bestModelSub);
  }

  private updatePredictionCharts() {
    if (this.predictions.length === 0) return;

    // Aggregate predictions across all clusters
    const aggregatedPredictions = this.aggregatePredictions();
    
    this.predictionSeries = [{
      name: 'Handover Predictions',
      data: Object.entries(aggregatedPredictions).map(([key, value]) => ({
        x: key.replace('_', ' ').toUpperCase(),
        y: value
      }))
    }];
  }

  private updateModelCharts() {
    if (Object.keys(this.modelPerformance).length === 0) return;

    const models = Object.keys(this.modelPerformance);
    const metrics = ['accuracy', 'precision', 'recall', 'f1_score'];
    
    this.modelSeries = metrics.map(metric => ({
      name: metric.toUpperCase(),
      data: models.map(model => ({
        x: model,
        y: (this.modelPerformance[model][metric as keyof ModelPerformance] as number) * 100
      }))
    }));
  }

  private generateRecommendations() {
    this.recommendations = [];
    this.riskAssessments = [];
    this.actionItems = [];

    this.predictions.forEach(prediction => {
      // Generate recommendations based on predictions
      if (prediction.confidence < 0.6) {
        this.recommendations.push({
          type: 'Model Improvement',
          priority: 'High',
          clusterId: prediction.cluster_id,
          message: `Low confidence (${(prediction.confidence * 100).toFixed(1)}%) for cluster ${prediction.cluster_id}`,
          action: 'Collect more training data or adjust model parameters',
          impact: 'Improve prediction accuracy by 15-20%'
        });
      }

      const dominantPred = prediction.dominant_prediction;
      if (dominantPred.includes('handover')) {
        this.recommendations.push({
          type: 'Network Optimization',
          priority: 'Medium',
          clusterId: prediction.cluster_id,
          message: `High ${dominantPred} probability for cluster ${prediction.cluster_id}`,
          action: 'Optimize handover parameters and cell boundaries',
          impact: 'Reduce handover failures by 10-15%'
        });
      }

      // Generate risk assessments
      const riskLevel = this.calculateRiskLevel(prediction);
      this.riskAssessments.push({
        clusterId: prediction.cluster_id,
        riskLevel,
        factors: this.getRiskFactors(prediction),
        mitigation: this.getMitigationStrategies(riskLevel)
      });

      // Generate action items
      if (prediction.confidence > 0.8 && dominantPred.includes('handover')) {
        this.actionItems.push({
          priority: 'High',
          title: `Prepare Handover for Cluster ${prediction.cluster_id}`,
          description: `High confidence (${(prediction.confidence * 100).toFixed(1)}%) ${dominantPred} predicted`,
          deadline: new Date(Date.now() + 3600000), // 1 hour from now
          assignee: 'Network Engineer',
          status: 'pending'
        });
      }
    });

    // Sort by priority
    this.recommendations.sort((a, b) => {
      const priorityOrder = { 'High': 3, 'Medium': 2, 'Low': 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });
  }

  private aggregatePredictions(): Record<string, number> {
    const aggregated: Record<string, number> = {
      no_handover: 0,
      intra_freq_handover: 0,
      inter_freq_handover: 0,
      inter_rat_handover: 0
    };

    this.predictions.forEach(prediction => {
      prediction.predictions.forEach(pred => {
        aggregated[pred.name] += pred.probability;
      });
    });

    // Average the values
    const count = this.predictions.length || 1;
    Object.keys(aggregated).forEach(key => {
      aggregated[key] = aggregated[key] / count;
    });

    return aggregated;
  }

  private calculateRiskLevel(prediction: ClusterPrediction): string {
    if (prediction.confidence < 0.5) return 'High';
    if (prediction.confidence < 0.7) return 'Medium';
    return 'Low';
  }

  private getRiskFactors(prediction: ClusterPrediction): string[] {
    const factors = [];
    
    if (prediction.confidence < 0.6) {
      factors.push('Low model confidence');
    }
    
    if (prediction.dominant_prediction.includes('inter_rat')) {
      factors.push('Inter-RAT handover complexity');
    }
    
    const features = prediction.features_used;
    if (features['sinr'] < 5) {
      factors.push('Poor signal quality');
    }
    if (features['velocity'] > 80) {
      factors.push('High mobility');
    }
    
    return factors;
  }

  private getMitigationStrategies(riskLevel: string): string[] {
    switch (riskLevel) {
      case 'High':
        return [
          'Immediate monitoring required',
          'Prepare backup resources',
          'Alert network operations team'
        ];
      case 'Medium':
        return [
          'Increase monitoring frequency',
          'Prepare contingency plans',
          'Review parameter settings'
        ];
      case 'Low':
        return [
          'Continue normal monitoring',
          'Log for trend analysis',
          'Periodic review'
        ];
      default:
        return ['Monitor situation'];
    }
  }

  // Action methods
  implementRecommendation(recommendation: any) {
    console.log('🚀 Implementing recommendation:', recommendation);
    // In real implementation, this would call backend API
  }

  executeActionItem(action: any) {
    console.log('⚡ Executing action item:', action);
    // In real implementation, this would update status and notify team
  }

  retrainModel(modelName: string) {
    console.log('🔄 Retraining model:', modelName);
    this.predictionService.retrainModel(modelName).subscribe({
      next: (response) => {
        console.log('✅ Model retrained successfully:', response);
      },
      error: (error) => {
        console.error('❌ Failed to retrain model:', error);
      }
    });
  }

  exportDecisionReport() {
    console.log('📤 Exporting decision support report...');
    // In real implementation, this would generate PDF/Excel report
  }

  // Utility methods
  getPriorityColor(priority: string): string {
    switch (priority) {
      case 'High': return '#ef4444';
      case 'Medium': return '#f59e0b';
      case 'Low': return '#10b981';
      default: return '#6b7280';
    }
  }

  getRiskColor(riskLevel: string): string {
    switch (riskLevel) {
      case 'High': return '#ef4444';
      case 'Medium': return '#f59e0b';
      case 'Low': return '#10b981';
      default: return '#6b7280';
    }
  }

  getModelAccuracy(model: string): number {
    return this.modelPerformance[model]?.accuracy * 100 || 0;
  }

  goToDashboard() {
    this.router.navigate(['/dashboard']);
  }

  goToExplainability() {
    this.router.navigate(['/explainability']);
  }

  // Template methods
  toggleNotes() {
    this.showNotes = !this.showNotes;
  }

  onParamChange(value: string) {
    this.selectedParam = this.parameters.find(p => p.label === value);
  }

  applyRecommended() {
    if (this.selectedParam) {
      this.selectedParam.current = this.selectedParam.recommended;
      this.showToast = true;
      setTimeout(() => {
        this.showToast = false;
      }, 3000);
    }
  }

  // Initialize data for template
  private initializeTemplateData() {
    // Initialize parameters
    this.parameters = [
      { label: 'Handover Threshold', current: 0.7, recommended: 0.8, insight: 'Higher threshold reduces false positives' },
      { label: 'Signal Quality', current: -85, recommended: -80, insight: 'Optimize for better coverage' },
      { label: 'Mobility Speed', current: 50, recommended: 45, insight: 'Lower speed improves handover accuracy' }
    ];

    // Initialize strategies
    this.strategies = [
      { name: 'Proactive Optimization', description: 'Anticipate network issues before they occur' },
      { name: 'Reactive Adjustment', description: 'Respond to current network conditions' },
      { name: 'Predictive Maintenance', description: 'Use ML to predict component failures' }
    ];

    // Initialize predictive alerts
    this.predictiveAlerts = [
      { type: 'warning', message: 'High handover probability in Zone A', time: '5 min ago' },
      { type: 'info', message: 'Model performance degradation detected', time: '12 min ago' },
      { type: 'critical', message: 'Signal quality drop in Cluster 77', time: '18 min ago' }
    ];

    // Initialize DSO predictions
    this.dso1Predictions = [
      { cluster: 77, prediction: 'No Handover', confidence: 0.92 },
      { cluster: 78, prediction: 'Intra-freq Handover', confidence: 0.88 }
    ];

    this.dso2Predictions = [
      { cluster: 79, prediction: 'Inter-freq Handover', confidence: 0.85 },
      { cluster: 80, prediction: 'No Handover', confidence: 0.91 }
    ];

    this.dso3Predictions = [
      { cluster: 81, prediction: 'Inter-RAT Handover', confidence: 0.78 },
      { cluster: 82, prediction: 'Intra-freq Handover', confidence: 0.89 }
    ];

    this.dso4Predictions = [
      { cluster: 83, prediction: 'No Handover', confidence: 0.94 },
      { cluster: 84, prediction: 'Inter-freq Handover', confidence: 0.82 }
    ];
  }

  // Zone selection methods
  onZoneChange(): void {
    console.log('Zone changed to:', this.selectedZone);
    this.loadDecisionSupportData();
  }

  getFilteredCells(): any[] {
    if (!this.selectedZone || this.selectedZone === 'all') {
      return this.dashboardCells;
    }
    
    return this.dashboardCells.filter(cell => 
      cell.zone === this.selectedZone || 
      cell.zone_id === this.selectedZone ||
      `Zone_${cell.cluster_id}` === this.selectedZone
    );
  }

  private loadDecisionSupportData(): void {
    // Load static data based on selected zone
    this.loadSimulatorData();
  }

  private loadSimulatorData(): void {
    // Static simulator data for 9 zones
    const zoneData = [
      { zone_id: 77, zone: 'Zone_77', cluster_id: 77, rsrp: -75, sinr: 18, ho_rate: 0.95, coverage: 0.98, cell_status: 'active' },
      { zone_id: 78, zone: 'Zone_78', cluster_id: 78, rsrp: -78, sinr: 16, ho_rate: 0.93, coverage: 0.96, cell_status: 'active' },
      { zone_id: 79, zone: 'Zone_79', cluster_id: 79, rsrp: -72, sinr: 19, ho_rate: 0.96, coverage: 0.99, cell_status: 'active' },
      { zone_id: 80, zone: 'Zone_80', cluster_id: 80, rsrp: -80, sinr: 15, ho_rate: 0.91, coverage: 0.94, cell_status: 'active' },
      { zone_id: 81, zone: 'Zone_81', cluster_id: 81, rsrp: -77, sinr: 17, ho_rate: 0.94, coverage: 0.97, cell_status: 'active' },
      { zone_id: 82, zone: 'Zone_82', cluster_id: 82, rsrp: -74, sinr: 18, ho_rate: 0.95, coverage: 0.98, cell_status: 'active' },
      { zone_id: 83, zone: 'Zone_83', cluster_id: 83, rsrp: -76, sinr: 16, ho_rate: 0.92, coverage: 0.95, cell_status: 'active' },
      { zone_id: 84, zone: 'Zone_84', cluster_id: 84, rsrp: -79, sinr: 15, ho_rate: 0.90, coverage: 0.93, cell_status: 'active' },
      { zone_id: 85, zone: 'Zone_85', cluster_id: 85, rsrp: -73, sinr: 19, ho_rate: 0.97, coverage: 0.99, cell_status: 'active' }
    ];
    
    this.dashboardCells = zoneData;
  }
}
