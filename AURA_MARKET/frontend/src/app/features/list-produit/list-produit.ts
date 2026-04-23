import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { CartService } from '../../core/services/cart.service';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-list-produit',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './list-produit.html',
  styleUrl: './list-produit.css'
})
export class ListProduitComponent implements OnInit {
  produits: Produit[] = [];
  offres: Offre[] = [];

  private productService = inject(ProductService);
  private cartService = inject(CartService);

  ngOnInit() {
    this.loadData();
  }

  addToCart(produit: Produit) {
    this.cartService.addToCart(produit);
    alert('Produit ajouté au panier !');
  }

  loadData() {
    this.productService.getProduits().subscribe(p => this.produits = p);
    this.productService.getOffres().subscribe(o => this.offres = o);
  }

  getActiveOffer(produitId: string): Offre | undefined {
    return this.offres.find(o => o.produitId === produitId);
  }
}
