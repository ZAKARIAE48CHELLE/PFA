import { Component, OnInit, inject, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService, Produit, Offre } from '../../core/services/product.service';
import { NegotiationService, Negociation, MessageNegociation } from '../../core/services/negotiation.service';
import { CartService } from '../../core/services/cart.service';
import { Router, RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-dashboard-acheteur',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './dashboard-acheteur.html',
  styleUrl: './dashboard-acheteur.css'
})
export class DashboardAcheteurComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollMe') private myScrollContainer?: ElementRef;
  
  negociations: Negociation[] = [];
  produits: Produit[] = [];
  selectedNego?: Negociation;
  isSending = false;
  statusMessage = '';
  statusType: 'success' | 'danger' = 'success';
  
  // Buyer Agent states
  autoNegoInProgress = false;
  autoNegoTarget: number = 0;
  aiSuggestion: string | undefined;
  sessionId = 'session_' + Math.random().toString(36).substring(7);
  negociationTerminee = false;
  prixFinal: number | undefined;

  private negoService = inject(NegotiationService);
  private productService = inject(ProductService);
  private cartService = inject(CartService);
  private router = inject(Router);
  messages: MessageNegociation[] = [];
  newMessagePrice: number | undefined;
  newMessageText: string = '';
  activeTab: 'MANUAL' | 'AUTO' = 'MANUAL';

  ngOnInit() {
    this.loadData();
  }

  showStatus(msg: string, type: 'success' | 'danger' = 'success') {
    this.statusMessage = msg;
    this.statusType = type;
    setTimeout(() => this.statusMessage = '', 5000);
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      if (this.myScrollContainer) {
        this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight;
      }
    } catch (err) { }
  }

  private fetchedIds = new Set<string>();

  loadData() {
    forkJoin({
      n: this.negoService.getNegociations(),
      p: this.productService.getProduits()
    }).subscribe({
      next: ({ n, p }) => {
        this.negociations = n;
        this.produits = p;

        if (this.selectedNego) {
          const updated = n.find(x => x.id === this.selectedNego!.id);
          if (updated) {
            this.selectedNego = updated;
          }
        } else if (n.length > 0) {
          this.selectNego(n[0]);
        }
        this.fetchMissingProducts();
      },
      error: (err) => {
        console.error('[DashboardAcheteur] Erreur lors du chargement des données:', err);
      }
    });
  }

  private fetchMissingProducts() {
    if (!this.negociations.length) return;
    
    const currentProductIds = new Set(this.produits.map(p => p.id));
    
    this.negociations.forEach(nego => {
      const pid = nego.produitId;
      if (pid && !currentProductIds.has(pid) && !this.fetchedIds.has(pid)) {
        this.fetchedIds.add(pid);
        this.productService.getProduitById(pid).subscribe({
          next: (p) => {
            if (p && !this.produits.some(x => x.id === p.id)) {
              this.produits = [...this.produits, p];
            }
          },
          error: () => {
            console.warn(`[DashboardAcheteur] Impossible de charger le produit ${pid}`);
          }
        });
      }
    });
  }

  selectNego(nego: Negociation) {
    this.selectedNego = nego;
    this.negociationTerminee = false;
    this.loadMessages(nego.id);
  }

  loadMessages(negoId: string) {
    this.negoService.getMessages(negoId).subscribe(m => {
      this.messages = m;
    });
  }

  getProduitForNego(produitId: string | undefined): Produit | undefined {
    if (!produitId) return undefined;
    return this.produits.find(p => p.id === produitId);
  }

  sendMessage() {
    if (!this.selectedNego || this.isSending) return;
    if (!this.newMessageText.trim() && !this.newMessagePrice) return;
    
    const price = this.newMessagePrice || 0;
    const text = this.newMessageText.trim();
    
    this.newMessagePrice = undefined;
    this.newMessageText = '';
    this.isSending = true;

    const content = text ? text : `Je propose un prix de ${price} MAD`;

    const userMsg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'ACHETEUR',
      content: content,
      price: price
    };

    this.negoService.saveMessage(userMsg).subscribe({
      next: () => {
        if (this.selectedNego) {
          this.selectedNego.rounds = (this.selectedNego.rounds || 0) + 1;
        }
        this.loadMessages(this.selectedNego!.id);
        this.isSending = false;
        this.loadData();
      },
      error: (err) => {
        console.error('Save message error:', err);
        this.showStatus("Impossible d'envoyer le message.", 'danger');
        this.isSending = false;
      }
    });
  }

  get currentPrixPlancher(): number {
    if (!this.selectedNego) return 0;
    const produit = this.getProduitForNego(this.selectedNego.produitId);
    return produit?.prixPlancher || this.selectedNego.prixInitial * 0.6;
  }

  get isBudgetInvalid(): boolean {
    return this.newMessagePrice !== undefined && this.newMessagePrice > 0 && this.newMessagePrice < this.currentPrixPlancher;
  }

  get isBudgetValid(): boolean {
    return this.newMessagePrice !== undefined && this.newMessagePrice >= this.currentPrixPlancher;
  }

  get budgetMargin(): string | null {
    if (this.newMessagePrice === undefined || !this.selectedNego || this.newMessagePrice < this.currentPrixPlancher) return null;
    const currentPrice = this.selectedNego.prixFinal || this.selectedNego.prixInitial;
    if (this.newMessagePrice < currentPrice) {
      // Return a descriptive string or a ratio instead of a raw margin against the secret min if preferred, 
      // but here we just hide the "minimum" from being subtracted.
      // We can just return 'Valide' or the distance to current price.
      return `✓ Votre budget est dans une zone négociable.`;
    }
    return null;
  }

  startAutoNego() {
    if (!this.selectedNego || !this.newMessagePrice || this.isSending) return;
    
    const target = this.newMessagePrice;
    const prixPlancher = this.currentPrixPlancher;
    const prixActuel = this.selectedNego.prixFinal || this.selectedNego.prixInitial;

    this.newMessagePrice = undefined;
    this.isSending = true;
    this.autoNegoInProgress = true;
    this.autoNegoTarget = target;

    const userMsg: MessageNegociation = {
      negociationId: this.selectedNego.id,
      sender: 'SYSTEM',
      content: `🤖 L'acheteur a lancé une négociation automatique avec un budget de ${target} MAD.`,
      price: target
    };

    this.negoService.saveMessage(userMsg).subscribe(() => {
      this.loadMessages(this.selectedNego!.id);
      
      this.negoService.startAcheteurNegoAuto(this.selectedNego!, target, prixPlancher, this.sessionId).subscribe({
        next: (res) => {
          this.autoNegoInProgress = false;

          let content = res.message || '';

          if (res.status === 'ACCEPTED') {
            this.negociationTerminee = true;
            const finalPrice = res.prixFinal || res.budget;
            this.prixFinal = finalPrice;
            this.selectedNego!.prixFinal = finalPrice;
            this.showStatus(`✅ Accord automatique trouvé à ${finalPrice} MAD !`);
            content = `🎉 Accord automatique trouvé à ${finalPrice} MAD.`;
          } else if (res.status === 'NO_AGREEMENT') {
            this.selectedNego!.prixFinal = res.prixFinal;
            this.showStatus(`Aucun accord automatique trouvé. Dernière offre du vendeur : ${res.prixFinal} MAD.`, 'danger');
            content = `Aucun accord automatique n'a été trouvé. Dernière proposition : ${res.prixFinal} MAD.`;
          } else if (res.status === 'INVALID_BUDGET') {
            this.showStatus('Budget insuffisant pour une négociation automatique.', 'danger');
            content = `Budget insuffisant pour une négociation automatique.`;
          }

          const agentMsg: MessageNegociation = {
            negociationId: this.selectedNego!.id,
            sender: 'SYSTEM',
            content: content,
            price: res.prixFinal || prixActuel
          };
          
          this.negoService.saveMessage(agentMsg).subscribe(() => {
            this.loadMessages(this.selectedNego!.id);
            this.isSending = false;
            this.loadData();
          });
        },
        error: (err) => {
          this.autoNegoInProgress = false;
          this.showStatus("L'assistant n'a pas pu démarrer la négociation automatique.", 'danger');
          this.isSending = false;
        }
      });
    });
  }

  askAISuggestion() {
    if (!this.selectedNego || this.isSending) return;
    
    this.isSending = true;
    const lastMsg = this.messages.length > 0 ? this.messages[this.messages.length-1].content : "Début de négo";

    this.negoService.sendAcheteurNegoMessage(lastMsg, this.selectedNego.id, this.sessionId).subscribe({
      next: (res) => {
        this.aiSuggestion = res.reponse;
        this.isSending = false;
      },
      error: () => {
        this.showStatus("Impossible de contacter l'assistant IA.", 'danger');
        this.isSending = false;
      }
    });
  }

  useAISuggestion() {
    if (!this.aiSuggestion) return;
    
    // Attempt to extract a price like "1200 MAD" or "1200.50 MAD" or just "1200"
    const match = this.aiSuggestion.match(/(\d+(?:[.,]\d+)?)/);
    if (match) {
      this.newMessagePrice = parseFloat(match[1].replace(',', '.'));
      this.showStatus("Prix suggéré appliqué !");
    }
    this.aiSuggestion = undefined;
  }

  deleteNego(event: Event, id: string) {
    event.stopPropagation();
    this.negoService.deleteNegociation(id).subscribe(() => {
      this.showStatus('Négociation supprimée');
      this.loadData();
      if (this.selectedNego?.id === id) {
        this.selectedNego = undefined;
        this.messages = [];
      }
    });
  }

  accepterOffre() {
    if (!this.selectedNego || this.isSending) return;
    
    const p = this.getProduitForNego(this.selectedNego.produitId);
    if (!p) return;

    this.isSending = true;
    this.showStatus("Acceptation en cours...");

    const negotiatedProduct = { 
      ...p, 
      prixNegocie: this.selectedNego.prixFinal 
    };

    this.cartService.addToCart(negotiatedProduct);
    
    this.isSending = false;
    this.router.navigate(['/checkout']);
  }

  selectOfferFromHistory(price: number) {
    if (this.selectedNego) {
      this.selectedNego.prixFinal = price;
    }
  }
}
