import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from 'src/app/demo/users/services/auth.service';

@Component({
  selector: 'app-auth-reset',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './auth-reset.html',
  styleUrl: './auth-reset.scss'
})
export class AuthReset {
  email = '';
  submitted = signal(false);
  success = signal(false);
  loading = signal(false);
  error = signal('');
  resetToken = signal('');

  constructor(private router: Router, private authService: AuthService) {}

  onSubmit() {
    this.submitted.set(true);
    this.error.set('');
    if (!this.email) return;

    this.loading.set(true);
    this.authService.forgotPassword({ email: this.email }).subscribe({
      next: (response) => {
        this.loading.set(false);
        // Extract token from response string
        const parts = response.split('Token: ');
        if (parts.length > 1) {
          this.resetToken.set(parts[1].trim());
        }
        this.success.set(true);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('Email not found. Please check and try again.');
      }
    });
  }
}