import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'mlflow',
    loadComponent: () =>
      import('./ml-lifecycle/ml-lifecycle').then(c => c.MlLifecycleComponent)
  },
  {
    path: 'ml-lifecycle',
    loadComponent: () =>
      import('./ml-lifecycle/ml-lifecycle').then(c => c.MlLifecycleComponent)
  },
  {
    path: 'ml-lifecycle/dso/:dsoId',
    loadComponent: () =>
      import('./dso-detail/dso-detail.component').then(c => c.DsoDetailComponent)
  },
  {
    path: 'retraining',
    loadComponent: () =>
      import('./retraining/retraining').then(c => c.RetrainingComponent)
  },
  {
    path: 'validation',
    loadComponent: () =>
      import('./validation/validation').then(c => c.ValidationComponent)
  },
  {
    path: 'reporting',
    loadComponent: () =>
      import('./reporting/reporting.component').then(c => c.DsReportingComponent)
  },
  {
    path: '',
    redirectTo: 'mlflow',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class DsRoutingModule {}
