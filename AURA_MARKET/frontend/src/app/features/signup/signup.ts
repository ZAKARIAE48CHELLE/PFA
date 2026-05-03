import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './signup.html',
  styleUrl: './signup.css'
})
export class SignupComponent {
  email = '';
  password = '';
  role = 'ACHETEUR'; // Default role
  error = '';
  isLoading = false;

  private authService = inject(AuthService);
  private router = inject(Router);

  onSignup() {
    if (!this.email || !this.password) {
      this.error = 'Veuillez remplir tous les champs';
      return;
    }

    this.isLoading = true;
    this.error = '';

    this.authService.register(this.email, this.password, this.role).subscribe({
      next: (user) => {
        this.isLoading = false;
        if (user.role === 'VENDEUR') {
          this.router.navigate(['/seller-dashboard']);
        } else if (user.role === 'ADMIN') {
          this.router.navigate(['/supervisor-dashboard']);
        } else {
          this.router.navigate(['/dashboard-acheteur']);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || 'Une erreur est survenue lors de l\'inscription';
      }
    });
  }
}
