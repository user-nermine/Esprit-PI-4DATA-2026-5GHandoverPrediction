import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from 'src/environments/environment';
import { AuthService } from 'src/app/demo/users/services/auth.service';

export interface UserResponse {
  id: number;
  fullName: string;
  email: string;
  role: string;
  status: string;
  lastLogin: string | null;
  createdAt: string;
}

export interface UserRequest {
  fullName: string;
  email: string;
  password?: string;
  role: string;
  status: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private baseUrl = `${environment.apiUrl}/users`;
  private auditUrl = `${environment.apiUrl}/audit-logs`;

  constructor(private http: HttpClient, private authService: AuthService) {}

  private saveAuditLog(action: string, target: string, status: string) {
    const user = this.authService.getCurrentUser();
    if (!user) return;
    this.http.post(this.auditUrl, {
      userName: user.fullName,
      userRole: user.role,
      action,
      target,
      status
    }).subscribe();
  }

  getAllUsers(): Observable<UserResponse[]> {
    return this.http.get<UserResponse[]>(this.baseUrl);
  }

  getUserById(id: number): Observable<UserResponse> {
    return this.http.get<UserResponse>(`${this.baseUrl}/${id}`);
  }

  createUser(request: UserRequest): Observable<UserResponse> {
    return this.http.post<UserResponse>(this.baseUrl, request).pipe(
      tap((created) => this.saveAuditLog('CREATE_USER', created.email, 'Success'))
    );
  }

  updateUser(id: number, request: UserRequest): Observable<UserResponse> {
    return this.http.put<UserResponse>(`${this.baseUrl}/${id}`, request).pipe(
      tap((updated) => this.saveAuditLog('UPDATE_USER', updated.email, 'Success'))
    );
  }

  deleteUser(id: number): Observable<void> {
    return this.http.get<UserResponse>(`${this.baseUrl}/${id}`).pipe(
      tap((user) => this.saveAuditLog('DELETE_USER', user.email, 'Success'))
    ) as any;
  }

  deleteUserById(id: number, email: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`).pipe(
      tap(() => this.saveAuditLog('DELETE_USER', email, 'Success'))
    );
  }

  toggleStatus(id: number, email: string): Observable<UserResponse> {
    return this.http.patch<UserResponse>(`${this.baseUrl}/${id}/toggle-status`, {}).pipe(
      tap((updated) => this.saveAuditLog('TOGGLE_STATUS', email, 'Success'))
    );
  }
}