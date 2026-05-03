import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ProductService, Produit } from '../../../core/services/product.service';

@Component({
  selector: 'app-detail-commande',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './detail-commande.html',
  styleUrl: './detail-commande.css'
})
export class DetailCommandeComponent implements OnInit {
  commande: any;
  produit?: Produit;
  loading = true;
  error = '';

  private route = inject(ActivatedRoute);
  private productService = inject(ProductService);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadData(id);
    }
  }

  loadData(id: string) {
    this.productService.getCommande(id).subscribe({
      next: (data) => {
        this.commande = data;
        // Load associated product details
        if (data.produitId) {
          this.productService.getProduitById(data.produitId).subscribe(p => this.produit = p);
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Load detail commande error:', err);
        this.error = 'Impossible de charger les détails de cette commande';
        this.loading = false;
      }
    });
  }

  getStatutBadgeClass(statut: string): string {
    switch (statut) {
      case 'PAYEE': return 'bg-success';
      case 'EN_ATTENTE_PAIEMENT': return 'bg-warning text-dark';
      case 'ANNULEE': return 'bg-danger';
      case 'EXPIREE': return 'bg-secondary';
      default: return 'bg-info';
    }
  }
  print() {
    window.print()
  }
}
