import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { adminGuard } from '../../core/guards/role.guard';

const routes: Routes = [
  {
    path: '',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./user-list/user-list').then(c => c.UserList)
  },
  {
    path: 'add',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./user-form/user-form').then(c => c.UserForm)
  },
  {
    path: 'edit/:id',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./user-form/user-form').then(c => c.UserForm)
  },
  {
    path: 'roles',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./user-roles/user-roles').then(c => c.UserRoles)
  },
  {
    path: 'audit-log',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./audit-log/audit-log').then(c => c.AuditLog)
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AdminRoutingModule {}
