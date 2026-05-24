// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AuthResponse {
  token: string;
  email: string;
  fullName: string;
  role: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  fullName: string;
  email: string;
  password: string;
  role: string;
}

// Rôles définis dans RoleEnum.java
export type UserRole =
  | 'SYSTEM_ADMIN'
  | 'DATA_SCIENTIST'
  | 'RAN_ENGINEER'
  | 'NOC_ENGINEER'
  | 'PERFORMANCE_ENGINEER';

// Routes par rôle — spec frontend
export const ROLE_ROUTES: Record<UserRole, string> = {
  SYSTEM_ADMIN:         '/dashboard',
  DATA_SCIENTIST:       '/data-scientist/mlflow',
  RAN_ENGINEER:         '/ran-engineer/kpi',
  NOC_ENGINEER:         '/monitoring',
  PERFORMANCE_ENGINEER: '/performance-view',
};

@Injectable({ providedIn: 'root' })
export class AuthService {

  // FIX: était :8080 → correct :8081
  private baseUrl = `${environment.apiUrl}`;

  private currentUserSubject = new BehaviorSubject<AuthResponse | null>(
    this.getUserFromStorage()
  );
  currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  // ── Auth endpoints (/api/auth — public, sans JWT) ──────────
  login(body: LoginRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/auth/login`, body).pipe(
      tap(res => this.setSession(res))
    );
  }

  register(body: RegisterRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/auth/register`, body).pipe(
      tap(res => this.setSession(res))
    );
  }

  forgotPassword(email: string): Observable<string> {
    return this.http.post(`${this.baseUrl}/auth/forgot-password`,
      { email }, { responseType: 'text' });
  }

  resetPassword(token: string, newPassword: string): Observable<string> {
    return this.http.post(`${this.baseUrl}/auth/reset-password`,
      { token, newPassword }, { responseType: 'text' });
  }

  // ── Session ────────────────────────────────────────────────
  private setSession(auth: AuthResponse): void {
    localStorage.setItem('token',    auth.token);
    localStorage.setItem('email',    auth.email);
    localStorage.setItem('fullName', auth.fullName);
    localStorage.setItem('role',     auth.role);
    this.currentUserSubject.next(auth);
  }

  logout(): void {
    localStorage.clear();
    this.currentUserSubject.next(null);
    this.router.navigate(['/auth/signin']);
  }

  // ── Getters ────────────────────────────────────────────────
  getToken(): string | null  { return localStorage.getItem('token'); }
  getRole(): UserRole | null { return localStorage.getItem('role') as UserRole | null; }
  getEmail(): string | null  { return localStorage.getItem('email'); }
  getFullName(): string | null { return localStorage.getItem('fullName'); }
  isLoggedIn(): boolean      { return !!this.getToken(); }

  getUserFromStorage(): AuthResponse | null {
    const token = localStorage.getItem('token');
    if (!token) return null;
    return {
      token,
      email:    localStorage.getItem('email')    || '',
      fullName: localStorage.getItem('fullName') || '',
      role:     localStorage.getItem('role')     || '',
    };
  }

  // ── Redirect après login selon rôle ───────────────────────
  redirectByRole(): void {
    const role = this.getRole();
    const route = role ? ROLE_ROUTES[role] : '/auth/signin';
    this.router.navigate([route]);
  }

  hasRole(...roles: UserRole[]): boolean {
    const role = this.getRole();
    return role ? roles.includes(role) : false;
  }
}