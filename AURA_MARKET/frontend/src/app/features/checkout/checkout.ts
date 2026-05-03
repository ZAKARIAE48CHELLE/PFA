import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CartService } from '../../core/services/cart.service';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './checkout.html',
  styleUrl: './checkout.css'
})
export class CheckoutComponent {
  cartService = inject(CartService);
  router = inject(Router);

  paymentData = {
    cardName: '',
    cardNumber: '',
    expiry: '',
    cvv: '',
    address: ''
  };

  isProcessing = false;
  isSuccess = false;

  processPayment() {
    this.isProcessing = true;
    
    // Simulate payment processing
    setTimeout(() => {
      this.isProcessing = false;
      this.isSuccess = true;
      this.cartService.clearCart();
    }, 2000);
  }
}
