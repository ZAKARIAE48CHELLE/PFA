import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { NegotiationService, Negociation, MessageNegociation } from '../../core/services/negotiation.service';
import flatpickr from 'flatpickr';
import { French } from 'flatpickr/dist/l10n/fr.js';
import { AuthService } from '../../core/services/auth.service';
import { NgxPaginationModule } from 'ngx-pagination';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { RouterModule } from '@angular/router';

Chart.register(...registerables);

@Component({
  selector: 'app-seller-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, BaseChartDirective, NgxPaginationModule, RouterModule],
  templateUrl: './seller-dashboard.html',
  styleUrl: './seller-dashboard.css'
})
export class SellerDashboardComponent implements OnInit {
  produits: Produit[] = [];
  userId: string = '';

  negociations: Negociation[] = [];
  selectedNego?: Negociation;
  messages: MessageNegociation[] = [];
  replyText: string = '';
  replyPrice: number | null = null;
  isSending: boolean = false;

  newProd: Partial<Produit> = {};
  editProd: Partial<Produit> & { id?: string } = {};
  selectedFile: File | null = null;

  // For Agent Securite alternatives
  showAlternatives: boolean = false;
  securityReason: string = '';
  alternativesOffre: number[] = [];
  editModalTab: 'info' | 'offers' = 'info';

  // For Adding new offer in modal
  isAddingOffer: boolean = false;
  isEditingOffer: boolean = false;
  editingOfferId: string | null = null;
  newOfferPrice: number | null = null;
  newOfferPercentage: number | null = null;
  newOfferStart: string = '';
  newOfferEnd: string = '';
  newOfferStatut: string = 'VALIDEE';

  // Inventory Filtering & Pagination
  inventorySearchQuery: string = '';
  itemsPerPage: number = 10;
  inventoryPage: number = 1;

  // KPIs
  totalStockValue = 0;
  lowStockCount = 0;
  outOfStockCount = 0;

  // Chart configs
  public categoryChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: [],
    datasets: [{ data: [], backgroundColor: ['#6366f1', '#f97316', '#10b981', '#f43f5e', '#8b5cf6'], hoverOffset: 4 }]
  };
  public categoryChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: 'right', labels: { color: '#64748b' } } },
    cutout: '70%'
  };

  public stockChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [{ data: [], label: 'Stock par Produit', backgroundColor: '#10b981', borderRadius: 6 }]
  };
  public stockChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
      x: { grid: { display: false }, ticks: { color: '#64748b' }, display: false } // Hide x-axis labels if too many products
    },
    plugins: { legend: { display: false } }
  };

  public topProductsChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [{ data: [], label: 'Ventes (MAD)', backgroundColor: '#3b82f6', borderRadius: 6 }]
  };
  public topProductsChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { beginAtZero: true, grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
      x: { grid: { display: false }, ticks: { color: '#64748b' }, display: false }
    },
    plugins: { legend: { display: false } }
  };

  private productService = inject(ProductService);
  private negoService = inject(NegotiationService);
  private authService = inject(AuthService);

  commandes: any[] = [];
  totalRevenue = 0;
  totalProductsCount = 0;
  activeTab: 'overview' | 'inventory' | 'orders' | 'negociations' = 'overview';
  pProduits: number = 1;
  pCommandes: number = 1;

  selectedCategory = 'Tous';
  categoriesList = ['Tous', 'Smartphones', 'Informatique', 'Gaming', 'Électroménager', 'Mode', 'Maison', 'Beauté', 'Sport'];

  changeCategory(cat: string) {
    this.selectedCategory = cat;
    this.inventoryPage = 1;
    this.loadProduits();
  }

  ngOnInit() {
    const user = this.authService.currentUserValue;
    if (user) {
      this.userId = user.id;
      this.loadProduits();
      this.loadNegociations();
    }
  }

  private fetchedProductIds = new Set<string>();

  get filteredProduits(): Produit[] {
    let list = this.produits;
    if (this.selectedCategory && this.selectedCategory !== 'Tous') {
      list = list.filter(p => p.categorie === this.selectedCategory);
    }
    if (this.inventorySearchQuery && this.inventorySearchQuery.trim()) {
      const q = this.inventorySearchQuery.toLowerCase();
      list = list.filter(p => p.titre && p.titre.toLowerCase().includes(q));
    }
    return list;
  }

  loadProduits() {
    const catParam = this.selectedCategory === 'Tous' ? undefined : this.selectedCategory;
    this.productService.getProduits(catParam).subscribe({
      next: p => {
        // Mock filtering by seller since API might return all
        this.produits = p.filter(pr => pr.vendeurId === this.userId || !pr.vendeurId);
        this.computeKPIs();
        this.loadCommandes();

        // Charger les offres pour chaque produit
        this.produits.forEach(prod => this.loadProductOffers(prod.id));
      },
      error: err => console.error('Erreur chargement produits:', err)
    });
  }

  loadCommandes() {
    this.productService.getCommandesByVendeur(this.userId).subscribe({
      next: c => {
        this.commandes = c;
        this.totalRevenue = c.reduce((sum, cmd) => sum + (cmd.prixFinal || 0), 0);
        this.updateCharts();
      },
      error: err => console.error('Erreur chargement commandes:', err)
    });
  }

  loadNegociations() {
    this.negoService.getSellerNegociations(this.userId).subscribe({
      next: n => {
        this.negociations = n;
        if (this.selectedNego) {
          const updated = n.find(x => x.id === this.selectedNego!.id);
          if (updated) this.selectedNego = updated;
        }
        this.fetchMissingProductsForNego();
      },
      error: err => console.error('Erreur chargement negociations:', err)
    });
  }

  private fetchMissingProductsForNego() {
    const currentIds = new Set(this.produits.map(p => p.id));
    this.negociations.forEach(nego => {
      const pid = nego.produitId;
      if (pid && !currentIds.has(pid) && !this.fetchedProductIds.has(pid)) {
        this.fetchedProductIds.add(pid);
        this.productService.getProduitById(pid).subscribe({
          next: p => {
            if (p && !this.produits.some(x => x.id === p.id)) {
              this.produits = [...this.produits, p];
            }
          }
        });
      }
    });
  }

  getProduitForNego(produitId: string): Produit | undefined {
    return this.produits.find(p => p.id === produitId);
  }

  selectNego(n: Negociation) {
    this.selectedNego = n;
    this.loadMessages(n.id);
  }

  loadMessages(negoId: string) {
    this.negoService.getMessages(negoId).subscribe({
      next: m => this.messages = m,
      error: err => console.error('Erreur messages:', err)
    });
  }

  sendReply() {
    if (!this.selectedNego || this.isSending) return;
    if (!this.replyText.trim() && !this.replyPrice) return;

    const text = this.replyText.trim();
    const price = this.replyPrice || 0;
    const content = text ? text : `Je propose une contre-offre à ${price} MAD`;

    this.isSending = true;
    const msg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'VENDEUR',
      content: content,
      price: price
    };

    this.negoService.saveMessage(msg).subscribe({
      next: () => {
        this.replyText = '';
        this.replyPrice = null;
        this.isSending = false;
        this.loadMessages(this.selectedNego!.id);
        this.loadNegociations();
      },
      error: err => {
        console.error('Erreur envoi message:', err);
        this.isSending = false;
      }
    });
  }

  accepterOffre(n: Negociation) {
    if (!n.prixFinal) return;
    this.isSending = true;
    this.negoService.acceptNegociation(n.id, n.prixFinal).subscribe({
      next: () => {
        this.isSending = false;
        this.loadMessages(n.id);
        this.loadNegociations();
      },
      error: err => {
        console.error('Erreur acceptation:', err);
        this.isSending = false;
      }
    });
  }

  computeKPIs() {
    this.totalStockValue = this.produits.reduce((acc, p) => acc + (p.prix * p.stock), 0);
    this.lowStockCount = this.produits.filter(p => p.stock > 0 && p.stock < 5).length;
    this.outOfStockCount = this.produits.filter(p => p.stock <= 0).length;
  }

  updateCharts() {
    this.productService.getCategoryStats().subscribe({
      next: stats => {
        this.totalProductsCount = Object.values(stats).reduce((acc, val) => acc + val, 0);
        this.categoryChartData = {
          labels: Object.keys(stats),
          datasets: [{
            data: Object.values(stats),
            backgroundColor: ['#6366f1', '#f97316', '#10b981', '#f43f5e', '#8b5cf6', '#a855f7', '#ec4899', '#06b6d4', '#eab308'],
            hoverOffset: 4
          }]
        };
      },
      error: err => console.error('Error loading category stats:', err)
    });

    // Stock Chart
    const activeProducts = this.produits.filter(p => p.stock > 0);
    this.stockChartData = {
      labels: activeProducts.map(p => p.titre),
      datasets: [{ data: activeProducts.map(p => p.stock), label: 'Stock par Produit', backgroundColor: '#10b981', borderRadius: 6 }]
    };

    // Top Products Chart
    const productRevenue: { [key: string]: number } = {};
    const productTitles: { [key: string]: string } = {};

    this.produits.forEach(p => productTitles[p.id] = p.titre);

    this.commandes.forEach(c => {
      const pid = c.produitId;
      productRevenue[pid] = (productRevenue[pid] || 0) + (c.prixFinal || 0);
    });

    const sortedProducts = Object.keys(productRevenue)
      .sort((a, b) => productRevenue[b] - productRevenue[a])
      .slice(0, 5); // top 5

    this.topProductsChartData = {
      labels: sortedProducts.map(id => productTitles[id] || 'Produit ' + id),
      datasets: [{ data: sortedProducts.map(id => productRevenue[id]), label: 'Ventes (MAD)', backgroundColor: '#3b82f6', borderRadius: 6 }]
    };
  }

  // --- Modal Logic ---
  onFileSelected(event: any, type: 'new' | 'edit') {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      const reader = new FileReader();
      reader.onload = (e: any) => {
        if (type === 'new') this.newProd.imageUrl = e.target.result;
        else this.editProd.imageUrl = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  onSubmit() {
    if (!this.newProd.titre || !this.newProd.prix) return;

    // Si une offre est renseignée, on demande à l'Agent Sécurité de l'analyser
    if (this.newProd.prixOffre && this.newProd.prixOffre > 0) {
      const payload = {
        type: 'OFFRE',
        prix: this.newProd.prixOffre,
        prixBase: this.newProd.prix || 0,
        categorie: this.newProd.categorie || 'autre',
        rating: 4.5 // Default seller rating for now
      };

      this.productService.verifierSecurite(payload).subscribe({
        next: (res) => {
          if (res.isSuspect || res.statut === 'SUSPECT' || res.statut === 'NON ACCEPTABLE') {
            this.showAlternatives = true;
            this.securityReason = res.raison || 'Prix suspect détecté par l\'Agent Sécurité.';
            this.alternativesOffre = res.alternatives || [];
          } else {
            this.proceedCreate();
          }
        },
        error: (err) => {
          console.error("Erreur sécurité:", err);
          this.proceedCreate(); // Fallback
        }
      });
    } else {
      this.proceedCreate();
    }
  }

  productOffers: { [key: string]: Offre[] } = {};

  proceedCreate() {
    this.newProd.vendeurId = this.userId;
    this.newProd.statut = 'ACTIF';

    this.productService.createProduit(this.newProd).subscribe({
      next: (createdProd) => {
        // Si un prix offre a été spécifié, on crée aussi l'enregistrement dans la classe Offre
        if (this.newProd.prixOffre && this.newProd.prixOffre > 0) {
          const offrePayload = {
            produitId: createdProd.id,
            prixPropose: this.newProd.prixOffre,
            prixFinal: this.newProd.prixOffre,
            statut: 'VALIDEE', // Puisqu'elle a passé le filtre de l'agent sécu (ou bypassé)
            titre: `Offre Spéciale: ${createdProd.titre}`,
            description: `Promotion initiale sur ${createdProd.titre}`
          };
          this.productService.createOffre(offrePayload).subscribe({
            next: () => {
              this.loadProduits();
              this.resetForm();
            },
            error: err => console.error("Erreur création offre:", err)
          });
        } else {
          this.loadProduits();
          this.resetForm();
        }
      },
      error: err => console.error(err)
    });
  }

  loadProductOffers(produitId: string) {
    this.productService.getOffresByProduit(produitId).subscribe({
      next: (offres) => {
        // Trier du plus récent au plus ancien
        this.productOffers[produitId] = offres.sort((a, b) =>
          new Date(b.dateCreation).getTime() - new Date(a.dateCreation).getTime()
        );

        // Dynamically assign active offer's prixFinal to p.prixOffre for display
        const prod = this.produits.find(p => p.id === produitId);
        if (prod) {
          const activeOffer = offres.find(o => this.isOfferActive(o));
          prod.prixOffre = activeOffer ? activeOffer.prixFinal : undefined;
        }
      },
      error: (err) => console.error("Erreur chargement offres produit:", err)
    });
  }

  selectAlternative(altPrix: number) {
    this.newProd.prixOffre = altPrix;
    this.showAlternatives = false;
    this.proceedCreate();
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

  openEditModal(p: Produit) {
    this.editProd = { ...p };
  }

  onUpdate() {
    if (!this.editProd.id) return;
    this.productService.updateProduit(this.editProd.id, this.editProd).subscribe({
      next: () => {
        this.loadProduits();
        this.editProd = {};
        this.editModalTab = 'info';
      },
      error: err => console.error(err)
    });
  }

  addNewOffer() {
    this.isAddingOffer = true;
    this.isEditingOffer = false;
    this.newOfferPrice = null;
    this.newOfferStart = new Date().toISOString().slice(0, 16);
    this.newOfferEnd = '';
    this.newOfferStatut = 'VALIDEE';
    this.showAlternatives = false;
    setTimeout(() => this.initFlatpickr(), 50);
  }

  editOffre(off: Offre) {
    this.isAddingOffer = true;
    this.isEditingOffer = true;
    this.editingOfferId = off.id;
    this.newOfferPrice = off.prixPropose; // Keep for reference if needed

    if (off.pourcentageDiscount && off.pourcentageDiscount > 0) {
      this.newOfferPercentage = off.pourcentageDiscount;
    } else if (off.prixPropose && this.editProd.prix) {
      this.newOfferPercentage = parseFloat((((this.editProd.prix - off.prixPropose) / this.editProd.prix) * 100).toFixed(2));
    } else {
      this.newOfferPercentage = null;
    }

    this.newOfferStart = off.dateDebut ? off.dateDebut.slice(0, 16) : '';
    this.newOfferEnd = off.dateFin ? off.dateFin.slice(0, 16) : '';
    this.newOfferStatut = off.statut;
    this.showAlternatives = false;
    setTimeout(() => this.initFlatpickr(), 50);
  }

  initFlatpickr() {
    const commonConfig: any = {
      enableTime: true,
      time_24hr: true,
      dateFormat: "Y-m-dTH:i",
      locale: French
    };

    flatpickr(".fp-start", {
      ...commonConfig,
      defaultDate: this.newOfferStart,
      onChange: (dates, dateStr) => this.newOfferStart = dateStr
    });

    flatpickr(".fp-end", {
      ...commonConfig,
      defaultDate: this.newOfferEnd,
      onChange: (dates, dateStr) => this.newOfferEnd = dateStr
    });
  }

  cancelAddOffer() {
    this.isAddingOffer = false;
    this.isEditingOffer = false;
    this.editingOfferId = null;
    this.showAlternatives = false;
  }

  verifyAndAddOffer() {
    if (!this.newOfferPercentage || this.newOfferPercentage <= 0 || this.newOfferPercentage >= 100) {
      alert("Veuillez saisir un pourcentage valide (entre 1 et 99).");
      return;
    }

    const basePrice = this.editProd.prix || 0;
    const calculatedPrice = basePrice * (1 - this.newOfferPercentage / 100);

    // EXIGENCE 1: Le prix proposé ne peut pas être inférieur au prixPlancher du produit
    if (calculatedPrice < (this.editProd.prixPlancher || 0)) {
      alert(`Erreur: La réduction de ${this.newOfferPercentage}% donne un prix de ${calculatedPrice.toFixed(2)} MAD, ce qui est inférieur au prix minimum autorisé (${this.editProd.prixPlancher} MAD).`);
      return;
    }

    // Validation des dates
    if (this.newOfferStart && this.newOfferEnd) {
      if (new Date(this.newOfferEnd) <= new Date(this.newOfferStart)) {
        alert("La date de fin doit être après la date de début.");
        return;
      }
    }

    const payload = {
      type: 'OFFRE',
      prix: calculatedPrice,
      prixBase: basePrice,
      categorie: this.editProd.categorie || 'autre',
      rating: 4.5
    };

    this.productService.verifierSecurite(payload).subscribe({
      next: (res) => {
        if (res.isSuspect || res.statut === 'SUSPECT' || res.statut === 'NON ACCEPTABLE') {
          this.showAlternatives = true;
          this.securityReason = res.raison || 'Prix suspect détecté par l\'Agent Sécurité.';
          this.alternativesOffre = res.alternatives || [];
        } else {
          this.submitOfferRecord(calculatedPrice, this.newOfferPercentage!);
        }
      },
      error: (err) => {
        console.error("Erreur sécurité:", err);
        this.submitOfferRecord(calculatedPrice, this.newOfferPercentage!);
      }
    });
  }

  selectAlternativeForNewOffer(altPrice: number) {
    const basePrice = this.editProd.prix || 0;
    // Calculate new percentage based on alternative price
    const newPercentage = ((basePrice - altPrice) / basePrice) * 100;

    this.newOfferPrice = altPrice;
    this.newOfferPercentage = parseFloat(newPercentage.toFixed(2));
    this.showAlternatives = false;
    this.submitOfferRecord(altPrice, this.newOfferPercentage);
  }

  deleteOffre(id: string) {
    if (confirm("Êtes-vous sûr de vouloir supprimer cette offre ?")) {
      this.productService.deleteOffre(id).subscribe({
        next: () => {
          if (this.editProd.id) this.loadProductOffers(this.editProd.id);
        },
        error: err => console.error("Erreur suppression offre:", err)
      });
    }
  }

  submitOfferRecord(prix: number, percentage: number) {
    if (!this.editProd.id) return;

    const offrePayload = {
      produitId: this.editProd.id,
      prixPropose: prix,
      prixFinal: prix,
      pourcentageDiscount: percentage,
      statut: this.newOfferStatut,
      titre: `Offre: ${this.editProd.titre}`,
      description: `Promotion gérée via dashboard`,
      dateDebut: this.newOfferStart,
      dateFin: this.newOfferEnd
    };

    if (this.isEditingOffer && this.editingOfferId) {
      this.productService.updateOffre(this.editingOfferId, offrePayload).subscribe({
        next: () => this.finalizeOfferSubmit(prix),
        error: err => console.error("Erreur update offre:", err)
      });
    } else {
      this.productService.createOffre(offrePayload).subscribe({
        next: () => this.finalizeOfferSubmit(prix),
        error: err => console.error("Erreur création offre:", err)
      });
    }
  }

  finalizeOfferSubmit(prix: number) {
    // Mettre à jour aussi le prixOffre du produit pour la synchro si c'est l'offre active
    this.editProd.prixOffre = prix;
    this.productService.updateProduit(this.editProd.id!, this.editProd).subscribe(() => {
      this.loadProduits();
      this.isAddingOffer = false;
      this.isEditingOffer = false;
      this.editingOfferId = null;
      this.showAlternatives = false;
      if (this.editProd.id) this.loadProductOffers(this.editProd.id);
    });
  }

  isOfferActive(off: Offre): boolean {
    if (off.statut !== 'VALIDEE') return false;

    const now = new Date();
    const start = off.dateDebut ? new Date(off.dateDebut) : null;
    const end = off.dateFin ? new Date(off.dateFin) : null;

    // EXIGENCE 3: Invalidation automatique si date de fin < date actuelle
    if (start && now < start) return false;
    if (end && now > end) return false;

    return true;
  }

  deleteProduct(id: string) {
    if (confirm("Supprimer ce produit ?")) {
      this.productService.deleteProduit(id).subscribe({
        next: () => this.loadProduits(),
        error: err => console.error(err)
      });
    }
  }

  triggerAgent(p: Produit) {
    this.productService.genererOffreAgent(p).subscribe({
      next: res => {
        alert(`L'Agent a généré une offre à ${res.prixSuggere} MAD (Remise: ${res.discountPercent}%)`);
      },
      error: err => console.error(err)
    });
  }

}
