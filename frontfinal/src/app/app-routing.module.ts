import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { AdminComponent } from './theme/layout/admin/admin.component';
import { GuestComponent } from './theme/layout/guest/guest.component';

import { authGuard } from './core/guards/auth.guard';
import { RoleRedirectGuard } from './core/guards/role-redirect.guard';

const routes: Routes = [
  // =========================
  // LANDING PAGE (DEFAULT)
  // =========================
  {
    path: 'landing',
    loadComponent: () =>
      import('./demo/pages/landing-page/landing-page.component')
        .then(m => m.LandingPageComponent)
  },

  // =========================
  // DEFAULT ROUTE (REDIRECT TO LANDING)
  // =========================
  {
    path: '',
    redirectTo: 'landing',
    pathMatch: 'full'
  },



  // =========================
  // HOME WITH ROLE REDIRECTION
  // =========================
  {
    path: 'home',
    canActivate: [authGuard, RoleRedirectGuard],
    component: AdminComponent
  },

  // =========================
  // AUTH PAGES
  // =========================
  {
    path: '',
    component: GuestComponent,
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-signin/auth-signin.component')
            .then((c) => c.AuthSigninComponent)
      },
      {
        path: 'reset-password',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-reset/auth-reset')
            .then((c) => c.AuthReset)
      },
      {
        path: 'new-password/:token',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-new-password/auth-new-password')
            .then((c) => c.AuthNewPassword)
      },
      {
        path: 'register',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-signup/auth-signup.component')
            .then((c) => c.AuthSignupComponent)
      }
    ]
  },

  // =========================
  // MAIN DASHBOARD AREA
  // =========================
  {
    path: '',
    component: AdminComponent,
    canActivate: [authGuard],
    children: [

      // =========================
      // ADMIN
      // =========================
      {
        path: 'admin',
        loadChildren: () =>
          import('./roles/admin/admin-routing.module')
            .then(m => m.AdminRoutingModule)
      },

      // =========================
      // BASIC UI
      // =========================
      {
        path: 'basic',
        loadChildren: () =>
          import('./demo/ui-elements/ui-basic/ui-basic.module')
            .then((m) => m.UiBasicModule)
      },

      {
        path: 'forms',
        loadComponent: () =>
          import('./demo/pages/form-element/form-element')
            .then((c) => c.FormElement)
      },

      {
        path: 'tables',
        loadComponent: () =>
          import('./demo/pages/tables/tbl-bootstrap/tbl-bootstrap.component')
            .then((c) => c.TblBootstrapComponent)
      },

      {
        path: 'apexchart',
        loadComponent: () =>
          import('./demo/pages/core-chart/apex-chart/apex-chart.component')
            .then((c) => c.ApexChartComponent)
      },

      {
        path: 'sample-page',
        loadComponent: () =>
          import('./demo/extra/sample-page/sample-page.component')
            .then((c) => c.SamplePageComponent)
      },

      // =========================
      // DATA SCIENTIST
      // =========================
      {
        path: 'data-scientist',
        loadChildren: () =>
          import('./roles/data-scientist/ds-routing.module')
            .then(m => m.DsRoutingModule)
      },

      // =========================
      // CORE ENGINEER
      // =========================
      {
        path: 'core-engineer',
        loadChildren: () =>
          import('./roles/core-engineer/core-routing.module')
            .then(m => m.CoreRoutingModule)
      },

      // =========================
      // REPORTING
      // =========================
      {
        path: 'report-generator',
        loadComponent: () =>
          import('./demo/pages/report-generator/report-generator')
            .then((c) => c.ReportGeneratorComponent)
      },

      // =========================
      // NOC ENGINEER
      // =========================
      {
        path: 'noc',
        loadChildren: () =>
          import('./roles/noc/noc-routing.module')
            .then(m => m.NocRoutingModule)
      },

      // =========================
      // RAN ENGINEER
      // =========================
      {
        path: 'ran-engineer',
        loadChildren: () =>
          import('./roles/ran/ran-routing.module')
            .then(m => m.RanRoutingModule)
      },


      // =========================
      // ZONES
      // =========================
      {
        path: 'zone-detail',
        loadComponent: () =>
          import('./demo/pages/zone-detail/zone-detail.component')
            .then((c) => c.ZoneDetailComponent)
      },

      {
        path: 'zone/:id',
        loadComponent: () =>
          import('./demo/pages/zone-detail/zone-detail.component')
            .then((c) => c.ZoneDetailComponent)
      },

      // =========================
      // GUIDE DES SEUILS
      // =========================
      {
        path: 'guide',
        loadComponent: () =>
          import('./demo/pages/dso-guide/dso-guide.component')
            .then((c) => c.DsoGuideComponent)
      }
    ]
  },

  // =========================
  // FALLBACK ROUTE
  // =========================
  {
    path: '**',
    redirectTo: 'landing'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}