import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { NgApexchartsModule } from 'ng-apexcharts';

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild([
      {
        path: '',
        loadComponent: () => import('./performance-view').then(c => c.PerformanceViewComponent)
      }
    ]),
    NgApexchartsModule
  ]
})
export class PerformanceViewModule { }
