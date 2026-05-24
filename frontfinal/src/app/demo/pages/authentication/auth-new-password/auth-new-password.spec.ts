import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthNewPassword } from './auth-new-password';

describe('AuthNewPassword', () => {
  let component: AuthNewPassword;
  let fixture: ComponentFixture<AuthNewPassword>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthNewPassword]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AuthNewPassword);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
