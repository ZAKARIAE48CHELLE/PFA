import { Routes } from '@angular/router';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './core/services/auth.service';

export const authGuard = (route: any, state: any) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  if (authService.getToken()) {
    return true;
  }
  return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

export const routes: Routes = [
  { path: '', redirectTo: '/list-produit', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./features/login/login').then(m => m.LoginComponent) },
  { path: 'signup', loadComponent: () => import('./features/signup/signup').then(m => m.SignupComponent) },
  {
    path: 'list-produit',
    loadComponent: () => import('./features/list-produit/list-produit').then(m => m.ListProduitComponent)
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/dashboard-acheteur/dashboard-acheteur').then(m => m.DashboardAcheteurComponent)
  },
  {
    path: 'vendeur',
    canActivate: [authGuard],
    loadComponent: () => import('./features/seller-dashboard/seller-dashboard').then(m => m.SellerDashboardComponent)
  },
  {
    path: 'superviseur',
    canActivate: [authGuard],
    loadComponent: () => import('./features/supervisor-dashboard/supervisor-dashboard').then(m => m.SupervisorDashboardComponent)
  },
  {
    path: 'produits/:id',
    loadComponent: () => import('./features/Produits/detail-produit/detail-produit').then(m => m.DetailProduit)
  },
  {
    path: 'cart',
    loadComponent: () => import('./features/cart/cart').then(m => m.CartComponent)
  },
  {
    path: 'checkout',
    canActivate: [authGuard],
    loadComponent: () => import('./features/checkout/checkout').then(m => m.CheckoutComponent)
  },
  {
    path: 'commandes',
    canActivate: [authGuard],
    loadComponent: () => import('./features/commandes/list-commandes/mes-commandes').then(m => m.MesCommandesComponent)
  },
  {
    path: 'commandes/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/commandes/detail-commandes/detail-commande').then(m => m.DetailCommandeComponent)
  },
  { path: '**', redirectTo: '/list-produit' }
];
