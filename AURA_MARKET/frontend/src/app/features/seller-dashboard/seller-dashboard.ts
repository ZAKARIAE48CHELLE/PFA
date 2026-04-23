import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit } from '../../core/services/product.service';

@Component({
  selector: 'app-seller-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './seller-dashboard.html',
  styleUrl: './seller-dashboard.css'
})
export class SellerDashboardComponent implements OnInit {
  produits: Produit[] = [];
  newProd: Partial<Produit> = {};
  editProd: Partial<Produit> & { id?: string } = {};

  private productService = inject(ProductService);
  ngOnInit() {
    this.loadProduits();
  }

  loadProduits() {
    this.productService.getProduits().subscribe(p => this.produits = p);
  }

  onSubmit() {
    this.productService.createProduit(this.newProd).subscribe({
      next: () => {
        this.loadProduits();
        this.newProd = {};
      },
      error: err => alert("Erreur lors de l'ajout")
    });
  }

  openEditModal(produit: Produit) {
    this.editProd = { ...produit };
  }

  onUpdate() {
    if (!this.editProd.id) return;
    this.productService.updateProduit(this.editProd.id, this.editProd).subscribe({
      next: () => {
        this.loadProduits();
        this.editProd = {};
      },
      error: err => alert("Erreur lors de la mise à jour")
    });
  }

  onFileSelected(event: any, mode: 'new' | 'edit') {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        const base64String = reader.result as string;
        if (mode === 'new') {
          this.newProd.imageUrl = base64String;
        } else {
          this.editProd.imageUrl = base64String;
        }
      };
      reader.readAsDataURL(file);
    }
  }

  deleteProduct(id: string) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')) return;
    this.productService.deleteProduit(id).subscribe({
      next: () => this.loadProduits(),
      error: err => alert("Erreur lors de la suppression")
    });
  }

  triggerAgent(produit: Produit) {
    this.productService.genererOffreAgent(produit).subscribe({
      next: (res) => alert(`L'Agent a généré une offre à ${res.prixSuggere} € (Remise: ${res.discountPercent}%)`),
      error: err => alert("Erreur lors de la génération de l'offre par l'agent")
    });
  }
}
