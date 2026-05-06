import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { CartService } from '../../core/services/cart.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class HomeComponent implements OnInit {
  produits: Produit[] = [];
  featuredProduits: Produit[] = [];
  flashDeals: Produit[] = [];
  categories: string[] = [];
  currentSlide = 0;
  offres: Offre[] = [];

  private productService = inject(ProductService);
  private cartService = inject(CartService);

  heroSlides = [
    {
      title: 'Les Meilleures Offres du Moment',
      subtitle: 'Jusqu\'à -40% sur l\'électronique et la mode. Offres limitées !',
      cta: 'Découvrir',
      gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
      icon: 'bi-lightning-charge-fill'
    },
    {
      title: 'Négociez Vos Prix avec l\'IA',
      subtitle: 'Notre agent intelligent vous propose automatiquement le meilleur prix.',
      cta: 'Explorer',
      gradient: 'linear-gradient(135deg, #f97316 0%, #f59e0b 50%, #eab308 100%)',
      icon: 'bi-robot'
    },
    {
      title: 'Livraison Rapide & Sécurisée',
      subtitle: 'Livraison gratuite dès 500 MAD. Paiement 100% sécurisé.',
      cta: 'Acheter',
      gradient: 'linear-gradient(135deg, #10b981 0%, #14b8a6 50%, #06b6d4 100%)',
      icon: 'bi-truck'
    }
  ];

  categoryList = [
    { name: 'Smartphones', icon: 'bi-phone', color: '#0ea5e9' },
    { name: 'Informatique', icon: 'bi-laptop', color: '#6366f1' },
    { name: 'Gaming', icon: 'bi-controller', color: '#ec4899' },
    { name: 'Électroménager', icon: 'bi-tools', color: '#f97316' },
    { name: 'Mode', icon: 'bi-handbag', color: '#f43f5e' },
    { name: 'Maison', icon: 'bi-house-heart', color: '#8b5cf6' },
    { name: 'Beauté', icon: 'bi-flower1', color: '#10b981' },
    { name: 'Sport', icon: 'bi-dribbble', color: '#f59e0b' }
  ];

  private slideInterval: any;

  ngOnInit() {
    this.productService.getProduits().subscribe(produits => {
      this.produits = produits;
      this.featuredProduits = this.produits.slice(0, 8);
      this.flashDeals = this.produits.filter(pr => pr.prixOffre != null).slice(0, 4);
      if (this.flashDeals.length === 0) {
          this.flashDeals = this.produits.filter(pr => pr.prix > 50).slice(0, 4);
      }
      this.categories = [...new Set(this.produits.map(pr => pr.categorie).filter(Boolean))];
    });
    this.startSlider();
  }

  getActiveOffer(produitId: string): Offre | undefined {
    const activeOffers = this.offres.filter(o => o.produitId === produitId && this.isOfferActive(o));
    if (activeOffers.length > 0) {
      activeOffers.sort((a, b) => new Date(b.dateDebut || 0).getTime() - new Date(a.dateDebut || 0).getTime());
      return activeOffers[0];
    }
    return undefined;
  }

  isOfferActive(off: Offre): boolean {
    if (off.statut !== 'VALIDEE') return false;
    
    const now = new Date();
    const start = off.dateDebut ? new Date(off.dateDebut) : null;
    const end = off.dateFin ? new Date(off.dateFin) : null;

    if (start && now < start) return false;
    if (end && now > end) return false;
    
    return true;
  }

  ngOnDestroy() {
    if (this.slideInterval) clearInterval(this.slideInterval);
  }

  startSlider() {
    this.slideInterval = setInterval(() => {
      this.currentSlide = (this.currentSlide + 1) % this.heroSlides.length;
    }, 5000);
  }

  goToSlide(index: number) {
    this.currentSlide = index;
    if (this.slideInterval) clearInterval(this.slideInterval);
    this.startSlider();
  }

  addToCart(p: Produit) {
    this.cartService.addToCart(p);
  }
}
