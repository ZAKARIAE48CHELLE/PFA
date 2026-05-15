import { Injectable, signal } from '@angular/core';
import { Produit } from './product.service';

export interface CartItem {
  produit: Produit;
  quantite: number;
}

@Injectable({
  providedIn: 'root'
})
export class CartService {
  private cartItems = signal<CartItem[]>(this.loadCart());

  // Expose items as a read-only signal
  items = this.cartItems.asReadonly();

  constructor() {
    // Sync to sessionStorage whenever the signal changes
    // (In a real app, you might use an effect, but for simplicity here:)
  }

  private loadCart(): CartItem[] {
    const saved = sessionStorage.getItem('aura_cart');
    return saved ? JSON.parse(saved) : [];
  }

  private saveCart(items: CartItem[]) {
    sessionStorage.setItem('aura_cart', JSON.stringify(items));
    this.cartItems.set(items);
  }

  addToCart(produit: Produit) {
    const current = this.cartItems();
    const existing = current.find(item => item.produit.id === produit.id);

    if (existing) {
      existing.quantite += 1;
      // Update price if a newer negotiated or offer price is provided
      if (produit.prixOffre) existing.produit.prixOffre = produit.prixOffre;
      if (produit.prixNegocie) existing.produit.prixNegocie = produit.prixNegocie;
      this.saveCart([...current]);
    } else {
      this.saveCart([...current, { produit, quantite: 1 }]);
    }
  }

  removeFromCart(produitId: string) {
    const current = this.cartItems();
    this.saveCart(current.filter(item => item.produit.id !== produitId));
  }

  updateQuantity(produitId: string, delta: number) {
    const current = this.cartItems();
    const item: any = current.find(i => i.produit.id === produitId);
    console.log('item===>', item)
    if (item) {
      if (delta == 1 && item.quantite >= item.produit.stock) {
        window.alert("vous aves depasser la quantite disponible")
        return;
      }
      item.quantite += delta;
      if (item.quantite < 0) {
        this.removeFromCart(produitId);
      } else {
        this.saveCart([...current]);
      }
    }
  }

  get getTotalPrice(): number {
    return this.cartItems().reduce((total, item) => {
      const price = item.produit.prixNegocie || item.produit.prixOffre || item.produit.prix;
      return total + (price * item.quantite);
    }, 0);
  }

  get getItemCount(): number {
    return this.cartItems().reduce((count, item) => count + item.quantite, 0);
  }

  clearCart() {
    this.saveCart([]);
  }
}
