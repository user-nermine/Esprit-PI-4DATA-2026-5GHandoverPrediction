// angular import
import { Component, output, OnInit } from '@angular/core';

// project import
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { NavLogoComponent } from './nav-logo/nav-logo.component';
import { NavContentComponent } from './nav-content/nav-content.component';
import { RoleBasedNavigationService, NavigationItem } from './role-based-navigation';

@Component({
  selector: 'app-navigation',
  imports: [SharedModule, NavLogoComponent, NavContentComponent],
  templateUrl: './navigation.component.html',
  styleUrls: ['./navigation.component.scss']
})
export class NavigationComponent implements OnInit {
  // public props
  NavCollapse = output();
  navCollapsedMob = output();
  navCollapsed: boolean;
  navCollapsedMobValue: boolean;
  windowWidth: number;
  navigationItems: any[] = [];

  // constructor
  constructor(private roleBasedNavigationService: RoleBasedNavigationService) {
    this.windowWidth = window.innerWidth;
    this.navCollapsedMobValue = false;
  }

  ngOnInit() {
    this.navigationItems = this.roleBasedNavigationService.getNavigationItems();
  }

  // public method
  navCollapse() {
    if (this.windowWidth >= 992) {
      this.navCollapsed = !this.navCollapsed;
      this.NavCollapse.emit();
    }
  }

  navCollapseMob() {
    if (this.windowWidth < 992) {
    }
  }
}
