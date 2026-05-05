import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit } from '../../core/services/product.service';
import { AuthService } from '../../core/services/auth.service';
import { NgxPaginationModule } from 'ngx-pagination';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, ChartConfiguration, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-seller-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, BaseChartDirective, NgxPaginationModule],
  templateUrl: './seller-dashboard.html',
  styleUrl: './seller-dashboard.css'
})
export class SellerDashboardComponent implements OnInit {
  produits: Produit[] = [];
  userId: string = '';

  newProd: Partial<Produit> = {};
  editProd: Partial<Produit> = {};
  selectedFile: File | null = null;

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
  private authService = inject(AuthService);

  commandes: any[] = [];
  totalRevenue = 0;
  activeTab: 'overview' | 'inventory' | 'orders' = 'overview';
  pProduits: number = 1;
  pCommandes: number = 1;

  ngOnInit() {
    const user = this.authService.currentUserValue;
    if (user) {
      this.userId = user.id;
      this.loadProduits();
    }
  }

  loadProduits() {
    this.productService.getProduits().subscribe({
      next: p => {
        // Mock filtering by seller since API might return all
        this.produits = p.filter(pr => pr.vendeurId === this.userId || !pr.vendeurId);
        this.computeKPIs();
        this.loadCommandes();
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

  computeKPIs() {
    this.totalStockValue = this.produits.reduce((acc, p) => acc + (p.prix * p.stock), 0);
    this.lowStockCount = this.produits.filter(p => p.stock > 0 && p.stock < 5).length;
    this.outOfStockCount = this.produits.filter(p => p.stock <= 0).length;
  }

  updateCharts() {
    // Category Chart
    const cats: { [key: string]: number } = {};
    this.produits.forEach(p => {
      const c = p.categorie || 'Autre';
      cats[c] = (cats[c] || 0) + 1;
    });
    this.categoryChartData = {
      labels: Object.keys(cats),
      datasets: [{ data: Object.values(cats), backgroundColor: ['#6366f1', '#f97316', '#10b981', '#f43f5e', '#8b5cf6'], hoverOffset: 4 }]
    };

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
  onFileSelected(event: any, type: 'new'|'edit') {
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
    this.newProd.vendeurId = this.userId;
    this.newProd.statut = 'ACTIF';
    
    this.productService.createProduit(this.newProd).subscribe({
      next: () => { this.loadProduits(); this.newProd = {}; },
      error: err => console.error(err)
    });
  }

  openEditModal(p: Produit) {
    this.editProd = { ...p };
  }

  onUpdate() {
    if (!this.editProd.id) return;
    this.productService.updateProduit(this.editProd.id, this.editProd).subscribe({
      next: () => { this.loadProduits(); this.editProd = {}; },
      error: err => console.error(err)
    });
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
      next: res => { alert("Agent de négociation déclenché avec succès!"); },
      error: err => console.error(err)
    });
  }
}
