import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from 'src/app/demo/users/services/auth.service';

@Component({
  selector: 'app-auth-new-password',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './auth-new-password.html',
  styleUrl: './auth-new-password.scss'
})
export class AuthNewPassword {
  password = '';
  confirmPassword = '';
  showPassword = signal(false);
  showConfirmPassword = signal(false);
  submitted = signal(false);
  success = signal(false);
  loading = signal(false);
  error = signal('');
  token = '';

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService
  ) {
    this.token = this.route.snapshot.paramMap.get('token') || '';
  }

  togglePassword() { this.showPassword.set(!this.showPassword()); }
  toggleConfirmPassword() { this.showConfirmPassword.set(!this.showConfirmPassword()); }

  onSubmit() {
    this.submitted.set(true);
    this.error.set('');

    if (!this.password || !this.confirmPassword) {
      this.error.set('Please fill in all fields.');
      return;
    }
    if (this.password.length < 8) {
      this.error.set('Password must be at least 8 characters.');
      return;
    }
    if (this.password !== this.confirmPassword) {
      this.error.set('Passwords do not match.');
      return;
    }

    this.loading.set(true);
    this.authService.resetPassword({ token: this.token, newPassword: this.password }).subscribe({
      next: () => {
        this.loading.set(false);
        this.success.set(true);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('Invalid or expired token. Please request a new reset link.');
      }
    });
  }
}