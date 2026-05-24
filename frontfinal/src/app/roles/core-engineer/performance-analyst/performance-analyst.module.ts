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
        loadComponent: () => import('./performance-analyst.component').then(c => c.PerformanceAnalystComponent)
      }
    ]),
    NgApexchartsModule
  ]
})
export class PerformanceAnalystModule { }
