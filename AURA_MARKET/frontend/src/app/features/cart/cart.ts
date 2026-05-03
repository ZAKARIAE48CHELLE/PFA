import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CartService } from '../../core/services/cart.service';
import { Produit } from '../../core/services/product.service';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './cart.html',
  styleUrl: './cart.css'
})
export class CartComponent {
  cartService = inject(CartService);

  get items() {
    return this.cartService.items();
  }

  updateQuantity(id: string, delta: number, produit ?:Produit) {
    this.cartService.updateQuantity(id, delta);
  }

  removeItem(id: string) {
    this.cartService.removeFromCart(id);
  }
}
