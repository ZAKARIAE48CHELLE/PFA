import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ProductService, Produit } from '../../../core/services/product.service';
import { AuthService } from '../../../core/services/auth.service';

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
  isGeneratingPdf = false;
  userEmail = 'acheteur@auramarket.ma';
  userName = 'Client AuraMarket';

  private route = inject(ActivatedRoute);
  private productService = inject(ProductService);
  private authService = inject(AuthService);

  ngOnInit() {
    this.extractUserInfo();
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadData(id);
    }
  }

  private extractUserInfo() {
    const user = this.authService.currentUserValue;
    if (user && user.token) {
      try {
        const payload = JSON.parse(atob(user.token.split('.')[1]));
        if (payload.sub) {
          this.userEmail = payload.sub;
          const namePart = this.userEmail.split('@')[0];
          this.userName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
        }
      } catch (e) {
        console.error('Could not extract user info from token');
      }
    }
  }

  loadData(id: string) {
    this.productService.getCommande(id).subscribe({
      next: (data) => {
        this.commande = data;
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

  downloadPDF() {
    if (this.isGeneratingPdf) return;
    this.isGeneratingPdf = true;

    // Use window.print() with our @media print styles — 
    // this is the ONLY 100% reliable way to get a perfect PDF from the browser.
    // The @media print CSS already hides the nav, buttons, etc. and formats the invoice.
    window.print();

    // Reset after a short delay (print dialog is synchronous-blocking on most browsers)
    setTimeout(() => {
      this.isGeneratingPdf = false;
    }, 1000);
  }
}
