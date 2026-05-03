import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ProductService } from '../../../core/services/product.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-mes-commandes',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './mes-commandes.html',
  styleUrl: './mes-commandes.css'
})
export class MesCommandesComponent implements OnInit {
  commandes: any[] = [];
  loading = true;
  error = '';

  private productService = inject(ProductService);
  private authService = inject(AuthService);
  window: any;
  ngOnInit() {
    this.loadCommandes();
  }

  loadCommandes() {
    const user = this.authService.currentUserValue;
    if (!user) {
      this.error = 'Veuillez vous connecter pour voir vos commandes';
      this.loading = false;
      return;
    }

    this.productService.getCommandesByAcheteur(user.id).subscribe({
      next: (data) => {
        this.commandes = data.sort((a: any, b: any) =>
          new Date(b.dateCommande).getTime() - new Date(a.dateCommande).getTime()
        );
        this.loading = false;
      },
      error: (err) => {
        console.error('Load commandes error:', err);
        this.error = 'Impossible de charger vos commandes';
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
}
