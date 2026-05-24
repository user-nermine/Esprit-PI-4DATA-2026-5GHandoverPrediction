// angular import
import { ChangeDetectorRef, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { email, Field, form, minLength, required } from '@angular/forms/signals';

// project import
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { AuthService, AuthRequest } from 'src/app/demo/users/services/auth.service';

@Component({
  selector: 'app-auth-signin',
  imports: [CommonModule, RouterModule, SharedModule, Field],
  templateUrl: './auth-signin.component.html',
  styleUrls: ['./auth-signin.component.scss']
})
export class AuthSigninComponent {
  private cd = inject(ChangeDetectorRef);
  private authService = inject(AuthService);

  submitted = signal(false);
  error = signal('');
  showPassword = signal(false);

  loginModal = signal<{ email: string; password: string }>({
    email: '',
    password: ''
  });

  loginForm = form(this.loginModal, (schemaPath) => {
    required(schemaPath.email, { message: 'Email is required' });
    email(schemaPath.email, { message: 'Enter a valid email address' });
    required(schemaPath.password, { message: 'Password is required' });
    minLength(schemaPath.password, 8, { message: 'Password must be at least 8 characters' });
  });

  onSubmit(event: Event) {
    this.submitted.set(true);
    this.error.set('');
    event.preventDefault();
    const credentials = this.loginModal();
    console.log('DEBUG - Sending to backend:', JSON.stringify(credentials));
    
    const authRequest: AuthRequest = {
      email: credentials.email,
      password: credentials.password
    };
console.log('DEBUG - Sending to backend:', JSON.stringify(authRequest));

    this.authService.login(authRequest).subscribe({
      next: (response) => {
        console.log('Login successful:', response);
        // Rediriger vers home pour que le guard de rôle redirige vers le bon dashboard
        window.location.href = '/home';
      },
      error: (err) => {
        console.error('Login failed:', err);
        this.error.set('Email ou mot de passe incorrect');
        this.submitted.set(false);
        this.cd.detectChanges();
      }
    });
  }

  togglePasswordVisibility() {
    this.showPassword.set(!this.showPassword());
  }
}

