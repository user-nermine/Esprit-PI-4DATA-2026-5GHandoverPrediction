import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./ran-dashboard/ran-dashboard.component').then(c => c.RanDashboardComponent)
  },
  {
    path: 'kpi',
    loadComponent: () =>
      import('./kpi/kpi.component').then(c => c.KpiComponent)
  },
  {
    path: 'anomaly',
    loadComponent: () =>
      import('./anomaly/anomaly.component').then(c => c.AnomalyComponent)
  },
  {
    path: 'ran-report',
    loadComponent: () =>
      import('./ran-report/ran-report.component').then(c => c.RanReportComponent)
  },
  {
    path: 'pdf-report/:type',
    loadComponent: () =>
      import('./pdf-report/pdf-report.component').then(c => c.PdfReportComponent)
  },
  {
    path: '',
    redirectTo: 'kpi',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class RanRoutingModule {}
