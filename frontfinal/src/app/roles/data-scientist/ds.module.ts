import { NgModule }            from '@angular/core';
import { CommonModule }        from '@angular/common';
import { FormsModule }         from '@angular/forms';
//import { NgChartsModule }      from 'ng2-charts';   // Chart.js

import { DsRoutingModule }     from './ds-routing.module';
import { MlLifecycleComponent } from './ml-lifecycle/ml-lifecycle';
import { RetrainingComponent }  from './retraining/retraining';
import { ValidationComponent }  from './validation/validation';
import { DeploymentComponent }  from './deployment/deployment';

@NgModule({
  /*declarations: [
    MlLifecycleComponent,
    RetrainingComponent,
    ValidationComponent,
    DeploymentComponent
  ],*/
  imports: [
    CommonModule,
    FormsModule,
    //NgChartsModule,
    DsRoutingModule,
    MlLifecycleComponent,
    RetrainingComponent,
    ValidationComponent,
    DeploymentComponent
  ]
})
export class DsModule {}