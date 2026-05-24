import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'monitoring',
    loadComponent: () =>
      import('./monitoring/monitoring.component').then(c => c.MonitoringComponent)
  },
  {
    path: 'reporting',
    loadComponent: () =>
      import('./reporting/reporting.component').then(c => c.ReportingComponent)
  },
  {
    path: '',
    redirectTo: 'monitoring',
    pathMatch: 'full'
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class NocRoutingModule {}
