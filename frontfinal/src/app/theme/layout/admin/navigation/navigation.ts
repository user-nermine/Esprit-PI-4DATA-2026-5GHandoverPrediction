import { AuthService } from 'src/app/demo/users/services/auth.service';

export interface NavigationItem {
  id: string;
  title: string;
  type: 'item' | 'collapse' | 'group';
  translate?: string;
  icon?: string;
  hidden?: boolean;
  url?: string;
  classes?: string;
  exactMatch?: boolean;
  external?: boolean;
  target?: boolean;
  breadcrumbs?: boolean;
  adminOnly?: boolean;
  children?: NavigationItem[];
}

export const NavigationItems: NavigationItem[] = [
    {
    id: 'user-management',
    title: 'User Management',
    type: 'group',
    icon: 'icon-user',
    adminOnly: true,
    children: [
      {
        id: 'user-list',
        title: 'All Users',
        type: 'item',
        url: '/users',
        classes: 'nav-item',
        icon: 'feather icon-users',
        adminOnly: true
      },
      {
        id: 'user-add',
        title: 'Add User',
        type: 'item',
        url: '/users/add',
        classes: 'nav-item',
        icon: 'feather icon-user-plus',
        adminOnly: true
      },
      {
        id: 'user-roles',
        title: 'Roles',
        type: 'item',
        url: '/users/roles',
        classes: 'nav-item',
        icon: 'feather icon-shield',
        adminOnly: true
      },
      {
        id: 'audit-log',
        title: 'Audit Log',
        type: 'item',
        url: '/users/audit-log',
        classes: 'nav-item',
        icon: 'feather icon-activity',
        adminOnly: true
      },
      {
        id: 'data-management',
        title: 'Data Management',
        type: 'item',
        url: '/users/data-management',
        classes: 'nav-item',
        icon: 'feather icon-database',
        adminOnly: true
      }
    ]
  },
      {
    id: 'data-scientist',
    title: 'Data Scientist',
    type: 'group',
    icon: 'icon-pie-chart',
    children: [
      {
        id: 'ml-lifecycle',
        title: 'ML Lifecycle',
        type: 'item',
        url: '/data-scientist/mlflow',
        icon: 'feather icon-git-branch',
        classes: 'nav-item'
      },
          ]
  }
];