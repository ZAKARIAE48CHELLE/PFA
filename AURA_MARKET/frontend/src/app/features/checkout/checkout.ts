import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CartService } from '../../core/services/cart.service';
import { ProductService } from '../../core/services/product.service';
import { AuthService } from '../../core/services/auth.service';
import { forkJoin } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './checkout.html',
  styleUrl: './checkout.css'
})
export class CheckoutComponent {
  cartService = inject(CartService);
  productService = inject(ProductService);
  authService = inject(AuthService);
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
    
    const userId = this.authService.currentUserValue?.id;
    if (!userId) {
      alert("Veuillez vous connecter pour finaliser la commande.");
      this.isProcessing = false;
      this.router.navigate(['/login']);
      return;
    }

    const items = this.cartService.items();
    if (items.length === 0) {
      alert("Votre panier est vide.");
      this.isProcessing = false;
      return;
    }

    // Process each cart item:
    // 1. Create a validated Offer (Achat Direct)
    // 2. Pay the Offer to create Commande and Paiement entities in the backend
    const checkoutRequests = items.map(item => {
      const price = item.produit.prixOffre || item.produit.prix;
      const totalItemPrice = price * item.quantite;

      const offrePayload = {
        produitId: item.produit.id,
        acheteurId: userId,
        prixPropose: totalItemPrice,
        prixFinal: totalItemPrice,
        statut: 'VALIDEE',
        titre: `Achat Direct: ${item.produit.titre}`,
        description: `Achat direct de ${item.quantite}x via panier`
      };

      return this.productService.createOffre(offrePayload).pipe(
        switchMap((createdOffre: any) => {
          return this.productService.payerOffre(createdOffre.id, {
            montant: totalItemPrice,
            methode: 'CARTE'
          });
        })
      );
    });

    forkJoin(checkoutRequests).subscribe({
      next: () => {
        this.isProcessing = false;
        this.isSuccess = true;
        this.cartService.clearCart();
      },
      error: (err) => {
        console.error("Payment and Checkout failed:", err);
        alert(err.error?.message || "Une erreur est survenue lors de la création de la commande. Veuillez réessayer.");
        this.isProcessing = false;
      }
    });
  }
}

