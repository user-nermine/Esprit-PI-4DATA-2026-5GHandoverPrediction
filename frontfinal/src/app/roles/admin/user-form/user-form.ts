import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { UserService, UserRequest } from '../services/user';

@Component({
  selector: 'app-user-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './user-form.html',
  styleUrl: './user-form.scss'
})
export class UserForm implements OnInit {
  isEditMode = false;
  userId: number | null = null;
  loading = signal(false);
  error = signal('');

  user: UserRequest = {
    fullName: '',
    email: '',
    password: '',
    role: 'RAN_ENGINEER',
    status: 'ACTIVE'
  };

  constructor(private route: ActivatedRoute, private router: Router, private userService: UserService) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.userId = +id;
      this.loading.set(true);
      this.userService.getUserById(this.userId).subscribe({
        next: (data) => {
          this.user = {
            fullName: data.fullName,
            email: data.email,
            password: '',
            role: data.role,
            status: data.status
          };
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Failed to load user.');
          this.loading.set(false);
        }
      });
    }
  }

  onSubmit() {
    this.error.set('');
    this.loading.set(true);

    const request: UserRequest = { ...this.user };
    if (!request.password) delete request.password;

    if (this.isEditMode && this.userId) {
      this.userService.updateUser(this.userId, request).subscribe({
        next: () => this.router.navigate(['/admin']),
        error: () => {
          this.error.set('Failed to update user.');
          this.loading.set(false);
        }
      });
    } else {
      this.userService.createUser(request).subscribe({
        next: () => this.router.navigate(['/admin']),
        error: (err) => {
          this.error.set(err.error?.message || 'Failed to create user.');
          this.loading.set(false);
        }
      });
    }
  }
}