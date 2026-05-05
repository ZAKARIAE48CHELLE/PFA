import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { AuthService } from './core/services/auth.service';
import { CartService } from './core/services/cart.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class AppComponent {
  authService = inject(AuthService);
  cartService = inject(CartService);
  router = inject(Router);
  searchQuery = '';

  getRoleLabel(): string {
    const role = this.authService.currentUserValue?.role;
    switch (role) {
      case 'VENDEUR': return 'Vendeur';
      case 'ACHETEUR': return 'Acheteur';
      case 'SUPERVISEUR': return 'Superviseur';
      default: return role || '';
    }
  }

  onSearch() {
    if (this.searchQuery.trim()) {
      this.router.navigate(['/list-produit'], { queryParams: { search: this.searchQuery.trim() } });
    } else {
      this.router.navigate(['/list-produit']);
    }
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
