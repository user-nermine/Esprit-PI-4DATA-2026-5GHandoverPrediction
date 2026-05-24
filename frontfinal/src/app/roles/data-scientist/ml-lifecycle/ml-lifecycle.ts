import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { PredictionService, ModelPerformance } from '../../../services/prediction.service';

export interface DSOCards {
  id: string;
  name: string;
  metrics: { label: string; value: string; }[];
  bestModel: string;
}

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'app-ml-lifecycle',
  templateUrl: './ml-lifecycle.html'
})
export class MlLifecycleComponent implements OnInit, OnDestroy {

  dsoCards: DSOCards[] = [];
  selectedZone: string = 'all';
  selectedClusterId: number | null = null;
  private sub: Subscription = new Subscription();

  private DSO_META: Record<string, { name: string; metricKeys: string[] }> = {
    DSO1: { name: 'HO Prediction',      metricKeys: ['f1_score', 'auc_roc']   },
    DSO2: { name: 'Signal Degradation', metricKeys: ['f1_score', 'auc_roc']   },
    DSO3: { name: 'Next Best Cell',     metricKeys: ['accuracy', 'recall']    },
    DSO4: { name: 'Handover Type',      metricKeys: ['f1_score', 'precision'] },
  };

  private METRIC_LABELS: Record<string, string> = {
    f1_score:  'F1',
    auc_roc:   'AUC-ROC',
    accuracy:  'Accuracy',
    precision: 'Precision',
    recall:    'Recall',
  };

  constructor(
    private router: Router,
    private predictionService: PredictionService
  ) {}

  ngOnInit(): void {
    this.buildFallbackCards();

    const perfSub = this.predictionService.modelPerformance$.subscribe(performance => {
      if (Object.keys(performance).length === 0) return;
      this.buildCardsFromPerformance(performance);
    });

    this.sub.add(perfSub);
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  onZoneChange(): void {
    if (this.selectedZone === 'all') {
      this.selectedClusterId = null;
    } else {
      this.selectedClusterId = parseInt(this.selectedZone.replace('zone-', ''));
    }
    console.log('Zone changed to:', this.selectedZone, '→ cluster', this.selectedClusterId);
  }

  get currentZoneLabel(): string {
    if (this.selectedZone === 'all') return 'Toutes les zones';
    return 'Zone ' + this.selectedZone.replace('zone-', '');
  }

  private buildCardsFromPerformance(performance: Record<string, ModelPerformance>): void {
    const dsoOrder = ['DSO1', 'DSO2', 'DSO3', 'DSO4'];

    this.dsoCards = dsoOrder.map((dso, i) => {
      const meta = this.DSO_META[dso];

      const dsoModels = Object.entries(performance)
        .filter(([key]) => key.endsWith(`_${dso}`));

      if (dsoModels.length === 0) return this.fallbackCard(dso, i);

      // Pick best model by f1_score
      const best = dsoModels.reduce((prev, curr) =>
        (curr[1].f1_score > prev[1].f1_score) ? curr : prev
      );

      const [bestKey, bestMetrics] = best;
      const modelName = bestKey.replace(`_${dso}`, '');

      const metrics = meta.metricKeys.map(key => ({
        label: this.METRIC_LABELS[key] || key,
        value: (bestMetrics[key as keyof ModelPerformance] as number)?.toFixed(4) ?? 'N/A'
      }));

      return { id: `dso${i + 1}`, name: meta.name, metrics, bestModel: modelName };
    });
  }

  private buildFallbackCards(): void {
    this.dsoCards = [
      { id: 'dso1', name: 'HO Prediction',
        metrics: [{ label: 'F1', value: '…' }, { label: 'AUC-ROC', value: '…' }],
        bestModel: 'Loading…' },
      { id: 'dso2', name: 'Signal Degradation',
        metrics: [{ label: 'F1', value: '…' }, { label: 'AUC-ROC', value: '…' }],
        bestModel: 'Loading…' },
      { id: 'dso3', name: 'Next Best Cell',
        metrics: [{ label: 'Accuracy', value: '…' }, { label: 'Recall', value: '…' }],
        bestModel: 'Loading…' },
      { id: 'dso4', name: 'Handover Type',
        metrics: [{ label: 'F1', value: '…' }, { label: 'Precision', value: '…' }],
        bestModel: 'Loading…' },
    ];
  }

  private fallbackCard(dso: string, i: number): DSOCards {
    const meta = this.DSO_META[dso];
    return {
      id: `dso${i + 1}`,
      name: meta.name,
      metrics: meta.metricKeys.map(k => ({
        label: this.METRIC_LABELS[k] || k,
        value: 'N/A'
      })),
      bestModel: 'N/A'
    };
  }

  navigateToDSODetails(dsoId: string): void {
    this.router.navigate(['/data-scientist/ml-lifecycle/dso', dsoId]);
  }

  generateReport(): void {
    this.router.navigate(['/data-scientist/reporting']);
  }

  getMetricPercentage(value: string): number {
    const n = parseFloat(value);
    return isNaN(n) ? 0 : Math.min(n * 100, 100);
  }

  getPerformanceScore(dso: DSOCards): string {
    const scores = dso.metrics.map(m => parseFloat(m.value)).filter(n => !isNaN(n));
    if (!scores.length) return 'N/A';
    return ((scores.reduce((a, b) => a + b, 0) / scores.length) * 100).toFixed(1) + '%';
  }

  isHighValue(value: string): boolean {
    return parseFloat(value) > 0.7;
  }

  getDSOIcon(dsoId: string): string {
    const icons: Record<string, string> = {
      dso1: 'icon-activity',
      dso2: 'icon-trending-up',
      dso3: 'icon-cpu',
      dso4: 'icon-zap'
    };
    return icons[dsoId] || 'icon-box';
  }
}