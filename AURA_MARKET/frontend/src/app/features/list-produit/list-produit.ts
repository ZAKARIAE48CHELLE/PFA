import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { CartService } from '../../core/services/cart.service';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { NgxPaginationModule } from 'ngx-pagination';

@Component({
  selector: 'app-list-produit',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, NgxPaginationModule],
  templateUrl: './list-produit.html',
  styleUrl: './list-produit.css'
})
export class ListProduitComponent implements OnInit {
  allProduits: Produit[] = [];
  produits: Produit[] = [];
  offres: Offre[] = [];
  categories: string[] = [];

  // Filters
  searchQuery = '';
  selectedCategories: Set<string> = new Set();
  priceMin: number | null = null;
  priceMax: number | null = null;
  inStockOnly = false;
  sortBy = 'default';
  viewMode: 'grid' | 'list' = 'grid';

  // Pagination
  page: number = 1;

  private productService = inject(ProductService);
  private cartService = inject(CartService);
  private route = inject(ActivatedRoute);

  ngOnInit() {
    this.productService.getProduits().subscribe(p => {
      this.allProduits = p;
      this.categories = [...new Set(p.map(pr => pr.categorie).filter(Boolean))];

      // Check for query params (category from nav, search from header)
      this.route.queryParams.subscribe(params => {
        if (params['category']) {
          this.selectedCategories.clear();
          this.selectedCategories.add(params['category']);
        }
        if (params['search']) {
          this.searchQuery = params['search'];
        }
        this.applyFilters();
      });
    });
    this.productService.getOffres().subscribe(o => this.offres = o);
  }

  addToCart(produit: Produit) {
    this.cartService.addToCart(produit);
  }

  toggleCategory(cat: string) {
    if (this.selectedCategories.has(cat)) {
      this.selectedCategories.delete(cat);
    } else {
      this.selectedCategories.add(cat);
    }
    this.applyFilters();
  }

  resetFilters() {
    this.searchQuery = '';
    this.selectedCategories.clear();
    this.priceMin = null;
    this.priceMax = null;
    this.inStockOnly = false;
    this.sortBy = 'default';
    this.applyFilters();
  }

  applyFilters() {
    let filtered = [...this.allProduits];

    // Search
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.titre.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.categorie && p.categorie.toLowerCase().includes(q))
      );
    }

    // Categories
    if (this.selectedCategories.size > 0) {
      filtered = filtered.filter(p => this.selectedCategories.has(p.categorie));
    }

    // Price range
    if (this.priceMin != null) {
      filtered = filtered.filter(p => p.prix >= this.priceMin!);
    }
    if (this.priceMax != null) {
      filtered = filtered.filter(p => p.prix <= this.priceMax!);
    }

    // Stock
    if (this.inStockOnly) {
      filtered = filtered.filter(p => p.stock > 0);
    }

    // Sort
    switch (this.sortBy) {
      case 'price-asc': filtered.sort((a, b) => a.prix - b.prix); break;
      case 'price-desc': filtered.sort((a, b) => b.prix - a.prix); break;
      case 'name-asc': filtered.sort((a, b) => a.titre.localeCompare(b.titre)); break;
      case 'newest': filtered.sort((a, b) => new Date(b.datePublication).getTime() - new Date(a.datePublication).getTime()); break;
    }

    this.produits = filtered;
  }

  get activeFilterCount(): number {
    let count = 0;
    if (this.searchQuery.trim()) count++;
    if (this.selectedCategories.size > 0) count++;
    if (this.priceMin != null || this.priceMax != null) count++;
    if (this.inStockOnly) count++;
    return count;
  }

  getActiveOffer(produitId: string): Offre | undefined {
    return this.offres.find(o => o.produitId === produitId);
  }
}
