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
  newProd: Partial<Produit> & { prixOffre?: number } = {};
  editProd: Partial<Produit> & { id?: string } = {};

  // For Agent Securite alternatives
  showAlternatives: boolean = false;
  securityReason: string = '';
  alternativesOffre: number[] = [];

  private productService = inject(ProductService);
  ngOnInit() {
    this.loadProduits();
  }

  loadProduits() {
    this.productService.getProduits().subscribe(p => this.produits = p);
  }

  onSubmit() {
    // Si une offre est renseignée, on demande à l'Agent Sécurité de l'analyser
    if (this.newProd.prixOffre && this.newProd.prixOffre > 0) {
      const payload = {
        type: 'OFFRE',
        prix: this.newProd.prixOffre,
        prixBase: this.newProd.prix || 0,
        categorie: this.newProd.categorie || 'autre',
        rating: 4.0 // Assuming a default note
      };

      this.productService.verifierSecurite(payload).subscribe({
        next: (res) => {
          // L'Agent ML a renvoyé un statut
          if (res.isSuspect || res.statut === 'SUSPECT' || res.statut === 'NON ACCEPTABLE') {
            this.showAlternatives = true;
            this.securityReason = res.raison || 'Prix suspect détecté. Veuillez choisir une alternative.';
            this.alternativesOffre = res.alternatives || [];
          } else {
            // ACCEPTABLE
            this.proceedCreate();
          }
        },
        error: (err) => {
          alert("Erreur lors de la vérification de l'offre par l'Agent Sécurité.");
        }
      });
    } else {
      // Sans offre, publication directe
      this.proceedCreate();
    }
  }

  proceedCreate() {
    // Optionally map prixOffre to a real backend field if the backend supports it,
    // or just let the backend handle the newProd payload.
    this.productService.createProduit(this.newProd).subscribe({
      next: () => {
        this.loadProduits();
        this.resetForm();
        // Hide modal natively if bootstrap is working, else handle via JS
        const closeBtn = document.getElementById('closeNewProductModal');
        if (closeBtn) closeBtn.click();
      },
      error: err => alert("Erreur lors de l'ajout")
    });
  }

  selectAlternative(altPrix: number) {
    this.newProd.prixOffre = altPrix;
    this.showAlternatives = false;
    this.proceedCreate(); // directly save after choice
  }

  cancelAlternative() {
    this.showAlternatives = false;
    this.newProd.prixOffre = undefined;
  }

  resetForm() {
    this.newProd = {};
    this.showAlternatives = false;
    this.alternativesOffre = [];
    this.securityReason = '';
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

