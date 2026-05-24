import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from 'src/environments/environment';

export interface AuthRequest { email: string; password: string; }
export interface AuthResponse { token: string; email: string; fullName: string; role: string; }
export interface ResetPasswordRequest { email: string; }
export interface NewPasswordRequest { token: string; newPassword: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = `${environment.apiUrl}/auth`;

  constructor(private http: HttpClient, private router: Router) {}

  login(request: AuthRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/login`, request).pipe(
      tap((response) => {
        localStorage.setItem('token', response.token);
        localStorage.setItem('user', JSON.stringify({
          email: response.email,
          fullName: response.fullName,
          role: response.role
        }));
      })
    );
  }

  forgotPassword(request: ResetPasswordRequest): Observable<string> {
    return this.http.post(`${this.baseUrl}/forgot-password`, request, { responseType: 'text' });
  }

  resetPassword(request: NewPasswordRequest): Observable<string> {
    return this.http.post(`${this.baseUrl}/reset-password`, request, { responseType: 'text' });
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  getCurrentUser(): { email: string; fullName: string; role: string } | null {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  isAdmin(): boolean {
    return this.getCurrentUser()?.role === 'SYSTEM_ADMIN';
  }
}