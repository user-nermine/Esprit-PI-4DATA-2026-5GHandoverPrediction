import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthReset } from './auth-reset';

describe('AuthReset', () => {
  let component: AuthReset;
  let fixture: ComponentFixture<AuthReset>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthReset]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AuthReset);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
