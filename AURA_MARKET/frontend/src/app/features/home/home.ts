import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ProductService, Produit } from '../../core/services/product.service';
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
      subtitle: 'Livraison gratuite dès 500  €. Paiement 100% sécurisé.',
      cta: 'Acheter',
      gradient: 'linear-gradient(135deg, #10b981 0%, #14b8a6 50%, #06b6d4 100%)',
      icon: 'bi-truck'
    }
  ];

  categoryList = [
    { name: 'Électronique', icon: 'bi-cpu', color: '#6366f1' },
    { name: 'Mode', icon: 'bi-handbag', color: '#ec4899' },
    { name: 'Maison', icon: 'bi-house-heart', color: '#f97316' },
    { name: 'Sport', icon: 'bi-dribbble', color: '#10b981' },
    { name: 'Beauté', icon: 'bi-flower1', color: '#f43f5e' },
    { name: 'Livres', icon: 'bi-book', color: '#8b5cf6' },
    { name: 'Auto', icon: 'bi-car-front', color: '#0ea5e9' },
    { name: 'Alimentation', icon: 'bi-cup-hot', color: '#f59e0b' }
  ];

  private slideInterval: any;

  ngOnInit() {
    this.productService.getProduits().subscribe(p => {
      this.produits = p;
      this.featuredProduits = p.slice(0, 8);
      this.flashDeals = p.filter(pr => pr.prix > 50).slice(0, 4);
      this.categories = [...new Set(p.map(pr => pr.categorie).filter(Boolean))];
    });
    this.startSlider();
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
