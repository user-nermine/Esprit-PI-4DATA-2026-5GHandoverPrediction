import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Retraining } from './retraining';

describe('Retraining', () => {
  let component: Retraining;
  let fixture: ComponentFixture<Retraining>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Retraining]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Retraining);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
