import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { UserService, UserResponse } from '../services/user';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './user-list.html',
  styleUrl: './user-list.scss'
})
export class UserList implements OnInit {
  searchTerm = '';
  users: UserResponse[] = [];
  loading = signal(false);
  error = signal('');

  constructor(private userService: UserService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.userService.getAllUsers().subscribe({
      next: (data) => {
        this.users = data;
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('Failed to load users. Please ensure the backend service is running and the database is accessible.');
        this.loading.set(false);
        console.error('Error loading users:', err);
      }
    });
  }

  filteredUsers(): UserResponse[] {
    return this.users.filter(u =>
      u.fullName.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
  }

  getRoleBadge(role: string): string {
    const map: { [key: string]: string } = {
      'SYSTEM_ADMIN': 'bg-danger',
      'DATA_SCIENTIST': 'bg-primary',
      'RAN_ENGINEER': 'bg-warning',
      'NOC_ENGINEER': 'bg-info'
    };
    return map[role] || 'bg-secondary';
  }

  toggleStatus(user: UserResponse) {
    this.userService.toggleStatus(user.id, user.email).subscribe({
      next: (updated) => {
        const index = this.users.findIndex(u => u.id === updated.id);
        if (index !== -1) this.users[index] = updated;
      },
      error: () => alert('Failed to toggle status.')
    });
  }

  deleteUser(user: UserResponse) {
    if (confirm(`Are you sure you want to delete ${user.fullName}?`)) {
      this.userService.deleteUserById(user.id, user.email).subscribe({
        next: () => {
          this.users = this.users.filter(u => u.id !== user.id);
        },
        error: () => alert('Failed to delete user.')
      });
    }
  }
}