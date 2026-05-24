import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'performance-view',
    loadComponent: () =>
      import('./performance-view/performance-view').then(c => c.PerformanceViewComponent)
  },
  {
    path: 'explainability',
    loadComponent: () =>
      import('./explainability/explainability').then(c => c.ExplainabilityComponent)
  },
  {
    path: 'reporting',
    loadComponent: () =>
      import('./reporting/reporting.component').then(c => c.CoreReportingComponent)
  },
  {
    path: '',
    redirectTo: 'performance-view',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class CoreRoutingModule {}
