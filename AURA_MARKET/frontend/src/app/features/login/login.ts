import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent {
  email = '';
  mdp = '';
  error = '';
  returnUrl = '/acheteur';

  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  constructor() {
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/acheteur';
  }

  fillCredentials(email: string) {
    this.email = email;
    this.mdp = 'password123';
  }

  onSubmit() {
    this.error = '';
    this.authService.login(this.email, this.mdp).subscribe({
      next: (res) => {
        // If there's a returnUrl (from Guard), use it. 
        // Otherwise use role-based default.
        if (this.route.snapshot.queryParams['returnUrl']) {
          this.router.navigateByUrl(this.returnUrl);
        } else {
          if (res.role === 'VENDEUR') this.router.navigate(['/vendeur']);
          else if (res.role === 'ACHETEUR') this.router.navigate(['/acheteur']);
          else if (res.role === 'SUPERVISEUR') this.router.navigate(['/superviseur']);
        }
      },
      error: (err) => {
        this.error = 'Identifiants incorrects ou serveur indisponible.';
        console.error(err);
      }
    });
  }
}
