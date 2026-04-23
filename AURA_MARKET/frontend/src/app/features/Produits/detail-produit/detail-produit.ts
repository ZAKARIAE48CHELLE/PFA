import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { ProductService, Produit } from '../../../core/services/product.service';
import { NegotiationService } from '../../../core/services/negotiation.service';
import { CartService } from '../../../core/services/cart.service';
import { AuthService } from '../../../core/services/auth.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-detail-produit',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './detail-produit.html',
  styleUrl: './detail-produit.css',
})
export class DetailProduit implements OnInit {
  produit?: Produit;
  loading = true;
  error = '';
  statusMessage = '';
  statusType: 'success' | 'danger' = 'success';

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private productService = inject(ProductService);
  private negoService = inject(NegotiationService);
  private cartService = inject(CartService);
  private authService = inject(AuthService);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadProduit(id);
    } else {
      this.error = 'Identifiant du produit manquant';
      this.loading = false;
    }
  }

  showStatus(msg: string, type: 'success' | 'danger' = 'success') {
    this.statusMessage = msg;
    this.statusType = type;
    setTimeout(() => this.statusMessage = '', 5000);
  }

  loadProduit(id: string) {
    this.productService.getProduitById(id).subscribe({
      next: (p) => {
        this.produit = p;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Impossible de charger les détails du produit';
        this.loading = false;
        console.error(err);
      }
    });
  }

  addToCart() {
    if (this.produit) {
      this.cartService.addToCart(this.produit);
      this.showStatus('Produit ajouté au panier !');
    }
  }

  initiateNego() {
    if (!this.produit) return;

    const user = this.authService.currentUserValue;
    if (!user) {
      this.showStatus('Veuillez vous connecter pour négocier', 'danger');
      setTimeout(() => {
        this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      }, 2000);
      return;
    }

    this.negoService.createNegociation({
      produitId: this.produit.id,
      acheteurId: user.id,
      rounds: 0,
      prixInitial: this.produit.prix,
      prixFinal: this.produit.prix // Start with base price
    }).subscribe({
      next: () => {
        this.showStatus('Négociation initiée ! Redirection...');
        setTimeout(() => this.router.navigate(['/dashboard']), 1500);
      },
      error: (err) => {
        console.error('Nego Error:', err);
        this.showStatus(err.error?.error || "Erreur lors de l'initiation.", 'danger');
      }
    });
  }
}
