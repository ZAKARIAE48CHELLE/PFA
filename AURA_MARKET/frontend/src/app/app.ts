import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, Router } from '@angular/router';
import { AuthService } from './core/services/auth.service';
import { CartService } from './core/services/cart.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class AppComponent {
  authService = inject(AuthService);
  cartService = inject(CartService);
  router = inject(Router);

  getRoleLabel(): string {
    const role = this.authService.currentUserValue?.role;
    switch (role) {
      case 'VENDEUR': return 'Vendeur';
      case 'ACHETEUR': return 'Acheteur';
      case 'SUPERVISEUR': return 'Superviseur';
      default: return role || '';
    }
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
